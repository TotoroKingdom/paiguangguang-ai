import { randomUUID } from "node:crypto";
import { expect, test, type TestInfo } from "@playwright/test";

function adminPassword(testInfo: TestInfo): string {
  const metadata = testInfo.config.metadata as { adminPassword?: string };
  if (!metadata.adminPassword) throw new Error("administrator bootstrap password is missing");
  return metadata.adminPassword;
}

test("shows a runtime error and recovers on the next send", async ({
  page,
  request,
}, testInfo) => {
  const origin = testInfo.project.use.baseURL ?? "http://127.0.0.1:3100";
  const password = "runtime-error-pass";
  const registered = await page.request.post("/api/v1/auth/register", {
    data: { password, passwordConfirm: password, nickname: "Runtime Error" },
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
    data: { expectedVersion: account.version, reason: "Runtime error E2E" },
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
    data: { title: "运行时错误恢复" },
    headers: { origin, "x-csrf-token": csrf },
  });
  expect(created.status()).toBe(201);
  const conversationId = (await created.json()).id;

  let failNext = true;
  await page.route("**/api/v1/assistant/runs/stream", async (route) => {
    if (failNext) {
      failNext = false;
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ error: { message: "模型服务暂不可用" } }),
      });
      return;
    }
    await route.continue();
  });

  await page.goto(`/assistant/chat/${conversationId}`);
  await page.getByRole("textbox", { name: "询问任何问题" }).fill("第一次请求失败");
  await page.getByRole("button", { name: "发送消息" }).click();
  await expect(page.getByText("模型服务暂不可用", { exact: false })).toBeVisible();
  await expect(page.getByRole("article", { name: "用户消息" })).toHaveCount(0);

  await page.getByRole("textbox", { name: "询问任何问题" }).fill("第二次请求成功");
  await page.getByRole("button", { name: "发送消息" }).click();
  await expect(page.getByRole("article", { name: "助手消息" }).last()).toContainText(
    "FakeProvider",
  );
  await expect(page.getByRole("article", { name: "用户消息" })).toHaveCount(1);
});
