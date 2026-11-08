import path from "node:path";
import { mkdirSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { expect, test, type TestInfo } from "@playwright/test";

function adminPassword(testInfo: TestInfo): string {
  const metadata = testInfo.config.metadata as { adminPassword?: string };
  if (!metadata.adminPassword) throw new Error("administrator bootstrap password is missing");
  return metadata.adminPassword;
}

function screenshotPath(testInfo: TestInfo, name: string): string {
  const directory = path.resolve(
    process.cwd(),
    "../docs-codex/feat02-platform-v1/screenshots",
  );
  mkdirSync(directory, { recursive: true });
  return path.join(directory, `${testInfo.project.name}-${name}.png`);
}

test("persists personal skills and files and restricts MCP to approved servers", async ({
  page,
  request,
}, testInfo) => {
  const origin = testInfo.project.use.baseURL ?? "http://127.0.0.1:3100";
  const password = "personal-pass-1";
  const register = await page.request.post("/api/v1/auth/register", {
    data: { password, passwordConfirm: password, nickname: "个人资源用户" },
    headers: { origin, "Idempotency-Key": randomUUID() },
  });
  expect(register.status()).toBe(201);
  const account = (await register.json()).user.accountNumber as string;

  const adminLogin = await request.post("/api/v1/auth/login", {
    data: { accountNumber: "1", password: adminPassword(testInfo) },
    headers: { origin },
  });
  expect(adminLogin.status()).toBe(200);
  const adminCookies = (await request.storageState()).cookies;
  const adminCsrf =
    adminCookies.find((item) => item.name === "paiguangguang_csrf")?.value ?? "";
  const pending = await request.get(`/api/v1/admin/users?q=${account}`);
  const item = (await pending.json()).items.find(
    (user: { accountNumber: string }) => user.accountNumber === account,
  );
  expect(item).toBeTruthy();
  const activated = await request.post(`/api/v1/admin/users/${item.id}/activate`, {
    data: { expectedVersion: item.version, reason: "个人资源 E2E" },
    headers: { origin, "x-csrf-token": adminCsrf },
  });
  expect(activated.status()).toBe(200);

  const userLogin = await page.request.post("/api/v1/auth/login", {
    data: { accountNumber: account, password },
    headers: { origin },
  });
  expect(userLogin.status()).toBe(200);

  await page.goto("/assistant/skills");
  await page.getByLabel("导入技能文件", { exact: true }).setInputFiles({
    name: "weekly.md",
    mimeType: "text/markdown",
    buffer: Buffer.from("# E2E 周报技能\n\n输出进展、风险与下一步。", "utf8"),
  });
  await expect(page.getByText("E2E 周报技能", { exact: true })).toBeVisible();
  const skills = await page.request.get("/api/v1/me/skills");
  expect(skills.status()).toBe(200);
  expect(
    (await skills.json()).items.some(
      (skill: { name: string }) => skill.name === "E2E 周报技能",
    ),
  ).toBe(true);
  await page.screenshot({
    path: screenshotPath(testInfo, "personal-skills"),
    animations: "disabled",
  });

  await page.goto("/assistant/files");
  await page.getByLabel("上传服务端文件", { exact: true }).setInputFiles({
    name: "personal-notes.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("server-owned personal file", "utf8"),
  });
  await expect(page.getByText("personal-notes.txt", { exact: true })).toBeVisible();
  const fileList = await page.request.get("/api/v1/me/files");
  expect(fileList.status()).toBe(200);
  const uploaded = (await fileList.json()).items.find(
    (file: { filename: string }) => file.filename === "personal-notes.txt",
  );
  expect(uploaded).toBeTruthy();
  const content = await page.request.get(`/api/v1/me/files/${uploaded.id}/content`);
  expect(await content.text()).toBe("server-owned personal file");
  await page.getByRole("button", { name: "删除文件：personal-notes.txt" }).click();
  await page.getByRole("button", { name: "确认删除", exact: true }).click();
  await expect(page.getByText("personal-notes.txt", { exact: true })).toHaveCount(0);
  await page.screenshot({
    path: screenshotPath(testInfo, "personal-files"),
    animations: "disabled",
  });

  const serverName = `E2E MCP ${Date.now()}`;
  const createdServer = await request.post("/api/v1/admin/mcp/servers", {
    data: {
      name: serverName,
      description: "平台批准的只读知识服务",
      endpointUrl: "https://example.com/mcp",
      transport: "http",
    },
    headers: { origin, "x-csrf-token": adminCsrf },
  });
  expect(createdServer.status()).toBe(201);

  await page.goto("/assistant/mcp");
  await expect(page.getByText(serverName, { exact: true })).toBeVisible();
  await expect(page.getByLabel("连接地址", { exact: true })).toHaveCount(0);
  await page.getByText(serverName, { exact: true }).click();
  await page.getByLabel("个人访问 Token（可选）", { exact: true }).fill("e2e-private-token");
  await page.getByRole("button", { name: "保存个人授权", exact: true }).click();
  await expect(page.getByText("已授权", { exact: false }).first()).toBeVisible();
  const connections = await page.request.get("/api/v1/me/mcp/connections");
  expect(connections.status()).toBe(200);
  expect((await connections.json()).items[0].hasCredential).toBe(true);
  await page.screenshot({
    path: screenshotPath(testInfo, "personal-mcp"),
    animations: "disabled",
  });
});
