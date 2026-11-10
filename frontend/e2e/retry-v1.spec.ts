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

  await page.route("**/api/v1/assistant/runs/stream", async (route) => {
    const response = await route.fetch();
    const body = await response.text();
    await route.fulfill({
      response,
      body:
        body +
        `data: ${JSON.stringify({
          type: "error",
          runId: "ui-synthetic-failure",
          code: "LLM_UPSTREAM_ERROR",
          message: "模型服务暂不可用",
        })}\n\n`,
    });
  });
  await page.route("**/api/v1/assistant/runs/retry/stream", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body:
        `data: ${JSON.stringify({ type: "chunk", content: "FakeProvider 重试成功" })}\n\n` +
        `data: ${JSON.stringify({
          type: "done",
          runId: "ui-synthetic-retry",
          status: "completed",
        })}\n\n`,
    });
  });

  await page.goto(`/assistant/chat/${conversationId}`);
  await page.getByRole("textbox", { name: "询问任何问题" }).fill("第一次失败");
  await page.getByRole("button", { name: "发送消息", exact: true }).click();
  await expect(page.getByRole("article", { name: "用户消息" })).toHaveCount(1);
  await page.getByRole("button", { name: "重试回复", exact: true }).click();
  await expect(page.getByRole("article", { name: "助手消息" }).last()).toContainText("FakeProvider 重试成功");
  await expect(page.getByRole("article", { name: "用户消息" })).toHaveCount(1);
});
