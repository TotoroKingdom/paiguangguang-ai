import { randomUUID } from "node:crypto";
import { expect, test, type TestInfo } from "@playwright/test";

function adminPassword(testInfo: TestInfo): string {
  const metadata = testInfo.config.metadata as { adminPassword?: string };
  if (!metadata.adminPassword) throw new Error("administrator bootstrap password is missing");
  return metadata.adminPassword;
}

test("retries a failed real-user run on the same assistant message", async ({
  page,
  request,
}, testInfo) => {
  const origin = testInfo.project.use.baseURL ?? "http://127.0.0.1:3100";
  const password = "retry-pass-1";
  const registered = await page.request.post("/api/v1/auth/register", {
    data: { password, passwordConfirm: password, nickname: "Retry E2E" },
    headers: { origin, "Idempotency-Key": randomUUID() },
  });
  expect(registered.status()).toBe(201);
  const account = (await registered.json()).user;

  const adminLogin = await request.post("/api/v1/auth/login", {
    data: { accountNumber: "1", password: adminPassword(testInfo) },
    headers: { origin },
  });
  expect(adminLogin.status()).toBe(200);
  const adminCookies = (await request.storageState()).cookies;
  const adminCsrf =
    adminCookies.find((item) => item.name === "paiguangguang_csrf")?.value ?? "";
  const activated = await request.post(`/api/v1/admin/users/${account.id}/activate`, {
    data: { expectedVersion: account.version, reason: "Retry E2E" },
    headers: { origin, "x-csrf-token": adminCsrf },
  });
  expect(activated.status()).toBe(200);

  await page.request.post("/api/v1/auth/login", {
    data: { accountNumber: account.accountNumber, password },
    headers: { origin },
  });
  const cookies = await page.context().cookies();
  const csrf = cookies.find((item) => item.name === "paiguangguang_csrf")?.value ?? "";
  const created = await page.request.post("/api/v1/conversations", {
    data: { title: "真实重试" },
    headers: { origin, "x-csrf-token": csrf },
  });
  expect(created.status()).toBe(201);
  const conversationId = (await created.json()).id;
  const failed = await page.request.post("/api/v1/assistant/runs", {
    data: {
      conversationId,
      clientTurnId: "retry-ui-first",
      text: "第一次失败",
      mode: "openai",
    },
    headers: { origin, "x-csrf-token": csrf },
  });
  expect(failed.status()).toBe(200);
  expect((await failed.json()).run.status).toBe("failed");

  await page.goto(`/assistant/chat/${conversationId}`);
  await expect(page.getByRole("article", { name: "用户消息" })).toHaveCount(1);
  await page.getByRole("button", { name: "重试回复", exact: true }).click();
  await expect(page.getByRole("article", { name: "助手消息" }).last()).toContainText(
    "FakeProvider",
  );
  await expect(page.getByRole("article", { name: "用户消息" })).toHaveCount(1);
});
