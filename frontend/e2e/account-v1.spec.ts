import path from "node:path";
import { mkdirSync } from "node:fs";
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

test("registers from 100+, waits for approval, activates, logs in and opens account center", async ({
  page,
  request,
}, testInfo) => {
  const origin = testInfo.project.use.baseURL ?? "http://127.0.0.1:3100";
  const password = "e2e-user-pass";

  await page.goto("/assistant/register");
  await page.getByLabel("密码（至少 6 位）", { exact: true }).fill(password);
  await page.getByLabel("确认密码", { exact: true }).fill(password);
  await page.getByLabel("昵称（可选）", { exact: true }).fill("E2E 用户");
  await page.getByRole("button", { name: "创建账号", exact: true }).click();
  await expect(page).toHaveURL(/\/assistant\/register\/success$/);
  await expect(page.getByRole("heading", { name: "账号已创建", exact: true })).toBeVisible();

  const account = (await page.getByTestId("account-number").innerText()).trim();
  const recovery = (await page.getByTestId("recovery-code").innerText()).trim();
  expect(Number(account)).toBeGreaterThanOrEqual(100);
  expect(recovery).toMatch(/^PGG-/);
  await page.screenshot({
    path: screenshotPath(testInfo, "register-success"),
    animations: "disabled",
  });

  await page.goto("/assistant/login");
  await page.getByLabel("数字账号", { exact: true }).fill(account);
  await page.getByLabel("密码", { exact: true }).fill(password);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(page).toHaveURL(/\/assistant\/pending$/);
  await expect(page.getByRole("heading", { name: "等待管理员审核", exact: true })).toBeVisible();

  const adminLogin = await request.post("/api/v1/auth/login", {
    data: { accountNumber: "1", password: adminPassword(testInfo) },
    headers: { origin },
  });
  expect(adminLogin.status()).toBe(200);
  const cookies = (await request.storageState()).cookies;
  const csrf = cookies.find((item) => item.name === "paiguangguang_csrf")?.value ?? "";
  expect(csrf).not.toBe("");
  const pending = await request.get("/api/v1/admin/users?status=PENDING");
  expect(pending.status()).toBe(200);
  const item = (await pending.json()).items.find(
    (user: { accountNumber: string }) => user.accountNumber === account,
  );
  expect(item).toBeTruthy();
  const activated = await request.post(`/api/v1/admin/users/${item.id}/activate`, {
    data: { expectedVersion: item.version, reason: "E2E 审核通过" },
    headers: { origin, "x-csrf-token": csrf },
  });
  expect(activated.status()).toBe(200);

  await page.getByRole("button", { name: "刷新状态", exact: true }).click();
  await expect(page.getByRole("heading", { name: "账号已激活", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "进入工作台", exact: true }).click();
  await expect(page).toHaveURL(/\/assistant$/);

  await page.goto("/assistant/me");
  await expect(page.getByRole("heading", { name: "个人中心", exact: true })).toBeVisible();
  await expect(page.getByText(account, { exact: true }).first()).toBeVisible();
  await page.screenshot({
    path: screenshotPath(testInfo, "account-center"),
    animations: "disabled",
  });

  await page.getByRole("button", { name: "退出登录", exact: true }).click();
  await expect(page).toHaveURL(/\/assistant\/login$/);

  await page.goto("/assistant/login?next=https://evil.example/steal");
  await page.getByLabel("数字账号", { exact: true }).fill(account);
  await page.getByLabel("密码", { exact: true }).fill(password);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(page).toHaveURL(/\/assistant$/);
  expect(new URL(page.url()).host).toBe(new URL(origin).host);
});
