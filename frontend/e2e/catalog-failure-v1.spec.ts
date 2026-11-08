import { randomUUID } from "node:crypto";
import { expect, test, type TestInfo } from "@playwright/test";

function adminPassword(testInfo: TestInfo): string {
  const metadata = testInfo.config.metadata as { adminPassword?: string };
  if (!metadata.adminPassword) throw new Error("administrator bootstrap password is missing");
  return metadata.adminPassword;
}

test("an active user's catalog failure never falls back to demo data", async ({
  page,
  request,
}, testInfo) => {
  const origin = testInfo.project.use.baseURL ?? "http://127.0.0.1:3100";
  const password = "catalog-failure-pass";
  const registered = await page.request.post("/api/v1/auth/register", {
    data: { password, passwordConfirm: password, nickname: "Catalog Failure" },
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
    data: { expectedVersion: account.version, reason: "Catalog failure E2E" },
    headers: { origin, "x-csrf-token": adminCsrf },
  });
  expect(activated.status()).toBe(200);
  await page.request.post("/api/v1/auth/login", {
    data: { accountNumber: account.accountNumber, password },
    headers: { origin },
  });

  await page.route("**/api/v1/capabilities", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ error: { message: "能力目录故障" } }),
    }),
  );
  await page.goto("/assistant/tools");
  await expect(page.getByText("能力目录故障", { exact: true })).toBeVisible();
  await expect(page.getByText("共 0 个工具", { exact: true })).toBeVisible();
  await expect(page.getByText("网页搜索", { exact: true })).toHaveCount(0);
});
