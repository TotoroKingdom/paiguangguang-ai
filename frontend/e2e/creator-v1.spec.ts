import { randomUUID } from "node:crypto";
import { expect, test, type TestInfo } from "@playwright/test";

function adminPassword(testInfo: TestInfo): string {
  const metadata = testInfo.config.metadata as { adminPassword?: string };
  if (!metadata.adminPassword) throw new Error("administrator bootstrap password is missing");
  return metadata.adminPassword;
}

test("creator creates, tests and submits a tool; admin approves and releases it", async ({
  page,
  request,
}, testInfo) => {
  const origin = testInfo.project.use.baseURL ?? "http://127.0.0.1:3100";
  const adminLogin = await request.post("/api/v1/auth/login", {
    data: { accountNumber: "1", password: adminPassword(testInfo) },
    headers: { origin },
  });
  expect(adminLogin.status()).toBe(200);
  const adminCookies = (await request.storageState()).cookies;
  const adminCsrf =
    adminCookies.find((item) => item.name === "paiguangguang_csrf")?.value ?? "";

  const creatorPassword = "creator-pass-1";
  const registered = await request.post("/api/v1/auth/register", {
    data: {
      password: creatorPassword,
      passwordConfirm: creatorPassword,
      nickname: "E2E Creator",
    },
    headers: { origin, "Idempotency-Key": randomUUID() },
  });
  expect(registered.status()).toBe(201);
  const creator = (await registered.json()).user;
  const activated = await request.post(`/api/v1/admin/users/${creator.id}/activate`, {
    data: { expectedVersion: creator.version, reason: "Creator E2E" },
    headers: { origin, "x-csrf-token": adminCsrf },
  });
  expect(activated.status()).toBe(200);
  const refreshed = await request.get(`/api/v1/admin/users/${creator.id}`);
  expect(refreshed.status()).toBe(200);
  const assigned = await request.patch(`/api/v1/admin/users/${creator.id}/roles`, {
    data: {
      role: "CREATOR",
      expectedVersion: (await refreshed.json()).version,
      reason: "Creator E2E",
    },
    headers: { origin, "x-csrf-token": adminCsrf },
  });
  expect(assigned.status()).toBe(200);

  const creatorLogin = await page.request.post("/api/v1/auth/login", {
    data: { accountNumber: creator.accountNumber, password: creatorPassword },
    headers: { origin },
  });
  expect(creatorLogin.status()).toBe(200);

  const name = `E2E Creator Tool ${Date.now()}`;
  await page.goto("/assistant/creator");
  await page.getByLabel("名称", { exact: true }).fill(name);
  await page.getByLabel("说明", { exact: true }).fill("由 Creator UI 创建");
  await page.getByRole("button", { name: "创建草稿", exact: true }).click();
  await expect(page.getByRole("cell", { name, exact: true })).toBeVisible();

  let row = page.getByRole("row").filter({ hasText: name });
  await row.getByRole("button", { name: "测试", exact: true }).click();
  await expect(row.getByText("passed", { exact: true })).toBeVisible();
  page.once("dialog", (dialog) => void dialog.accept("请审核"));
  await row.getByRole("button", { name: "提交审核", exact: true }).click();
  await expect(row.getByText("submitted", { exact: true })).toBeVisible();

  const adminPageLogin = await page.request.post("/api/v1/auth/login", {
    data: { accountNumber: "1", password: adminPassword(testInfo) },
    headers: { origin },
  });
  expect(adminPageLogin.status()).toBe(200);
  await page.goto("/assistant/admin/reviews");
  row = page.getByRole("row").filter({ hasText: name });
  page.once("dialog", (dialog) => void dialog.accept("通过审核"));
  await row.getByRole("button", { name: "批准", exact: true }).click();

  const releaseRow = page.getByRole("row").filter({ hasText: name });
  page.once("dialog", (dialog) => void dialog.accept("发布 E2E 版本"));
  await releaseRow.getByRole("button", { name: "发布", exact: true }).click();
  await expect(page.getByText("已发布。", { exact: false })).toBeVisible();
});

test("creator submits an MCP server and only admin can approve it", async ({
  page,
  request,
}, testInfo) => {
  const origin = testInfo.project.use.baseURL ?? "http://127.0.0.1:3100";
  const adminLogin = await request.post("/api/v1/auth/login", {
    data: { accountNumber: "1", password: adminPassword(testInfo) },
    headers: { origin },
  });
  expect(adminLogin.status()).toBe(200);
  const adminCookies = (await request.storageState()).cookies;
  const adminCsrf =
    adminCookies.find((item) => item.name === "paiguangguang_csrf")?.value ?? "";
  const password = "creator-mcp-pass";
  const registered = await page.request.post("/api/v1/auth/register", {
    data: {
      password,
      passwordConfirm: password,
      nickname: "MCP Creator",
    },
    headers: { origin, "Idempotency-Key": randomUUID() },
  });
  expect(registered.status()).toBe(201);
  const creator = (await registered.json()).user;
  await request.post(`/api/v1/admin/users/${creator.id}/activate`, {
    data: { expectedVersion: creator.version, reason: "MCP Creator E2E" },
    headers: { origin, "x-csrf-token": adminCsrf },
  });
  const refreshed = await request.get(`/api/v1/admin/users/${creator.id}`);
  const assigned = await request.patch(`/api/v1/admin/users/${creator.id}/roles`, {
    data: {
      role: "CREATOR",
      expectedVersion: (await refreshed.json()).version,
      reason: "MCP Creator E2E",
    },
    headers: { origin, "x-csrf-token": adminCsrf },
  });
  expect(assigned.status()).toBe(200);
  await page.request.post("/api/v1/auth/login", {
    data: { accountNumber: creator.accountNumber, password },
    headers: { origin },
  });

  const name = `Creator MCP ${Date.now()}`;
  await page.goto("/assistant/creator");
  await page.getByLabel("MCP 服务名称", { exact: true }).fill(name);
  await page.getByLabel("MCP 说明", { exact: true }).fill("Creator 提交待审服务");
  await page
    .getByLabel("MCP HTTPS 地址", { exact: true })
    .fill("https://1.1.1.1/rpc");
  await page.getByRole("button", { name: "提交 MCP Server", exact: true }).click();
  await expect(
    page.getByText(`MCP Server“${name}”已提交，等待 Admin 审核。`, { exact: true }),
  ).toBeVisible();

  const pending = await request.get("/api/v1/admin/mcp/servers");
  const server = (await pending.json()).items.find(
    (item: { name: string }) => item.name === name,
  );
  expect(server.status).toBe("pending");
  const approved = await request.post(`/api/v1/admin/mcp/servers/${server.id}/approve`, {
    data: { reason: "Creator MCP E2E" },
    headers: { origin, "x-csrf-token": adminCsrf },
  });
  expect(approved.status()).toBe(200);
  const visible = await page.request.get("/api/v1/mcp/servers");
  expect(
    (await visible.json()).items.some((item: { id: string }) => item.id === server.id),
  ).toBe(true);
});
