import { expect, test, type Page, type TestInfo } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { mkdirSync } from "node:fs";
import path from "node:path";

function credentials(testInfo: TestInfo): { username: string; password: string } {
  const metadata = testInfo.config.metadata as {
    adminUsername?: string;
    adminPassword?: string;
  };
  if (!metadata.adminUsername || !metadata.adminPassword) {
    throw new Error("Playwright administrator bootstrap credentials are missing");
  }
  return { username: metadata.adminUsername, password: metadata.adminPassword };
}

function screenshotPath(testInfo: TestInfo, name: string): string {
  const directory = path.resolve(
    process.cwd(),
    "../docs-codex/assistant-capability-console-v1/screenshots",
  );
  mkdirSync(directory, { recursive: true });
  return path.join(directory, `${testInfo.project.name}-${name}.png`);
}

async function login(page: Page, testInfo: TestInfo) {
  const { username, password } = credentials(testInfo);
  await page.goto("/assistant/admin/login");
  await page.screenshot({
    path: screenshotPath(testInfo, "admin-login"),
    animations: "disabled",
  });
  await page.getByLabel("管理员用户名", { exact: true }).fill(username);
  await page.getByLabel("管理员密码", { exact: true }).fill(password);
  await page.getByRole("button", { name: "安全登录", exact: true }).click();
  await expect(page).toHaveURL(/\/assistant\/admin$/);
  await expect(
    page.getByRole("heading", { name: "能力治理，从这里开始", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: screenshotPath(testInfo, "admin-dashboard"),
    animations: "disabled",
  });
}

async function openAccountMenu(page: Page) {
  await page.getByRole("button", { name: "账户菜单", exact: true }).click();
  return page.getByRole("menu", { name: "账户菜单" });
}

test("anonymous visitors are redirected and admin APIs reject them", async ({
  page,
  request,
}) => {
  await page.goto("/assistant/admin");
  await expect(page).toHaveURL(/\/assistant\/admin\/login\?next=/);
  await expect(
    page.getByRole("heading", { name: "管理控制台登录", exact: true }),
  ).toBeVisible();
  const response = await request.get("/api/v1/admin/capabilities");
  expect(response.status()).toBe(401);
});

test("publishes a capability, proves draft isolation, disables it, and exposes the admin entry", async ({
  page,
}, testInfo) => {
  const name = `E2E 对账工具-${testInfo.project.name}`;
  const versionTwo = `${name} V2`;
  await login(page, testInfo);

  await page.goto("/assistant/admin/tools");
  await expect(page.getByRole("heading", { name: "工具管理", exact: true })).toBeVisible();
  await expect(page.getByText("网页搜索", { exact: true })).toBeVisible();
  await page.screenshot({
    path: screenshotPath(testInfo, "admin-tools-list"),
    animations: "disabled",
  });
  await page.getByRole("button", { name: "新建工具", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "新建能力", exact: true });
  await dialog.getByLabel("能力名称", { exact: true }).fill(name);
  await dialog.getByLabel("描述", { exact: true }).fill("验证草稿、发布、停用与用户目录联动。");
  await dialog.getByLabel("分类", { exact: true }).fill("E2E");
  await dialog.getByRole("button", { name: "创建并编辑", exact: true }).click();
  await expect(page).toHaveURL(/\/assistant\/admin\/capabilities\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { name, exact: true })).toBeVisible();
  const detailUrl = page.url();
  await page.screenshot({
    path: screenshotPath(testInfo, "admin-capability-detail"),
    animations: "disabled",
  });

  await page
    .getByLabel("执行步骤（每行一个）", { exact: true })
    .fill("读取流水\n比对总账\n输出差异");
  await page.getByRole("button", { name: "保存草稿", exact: true }).first().click();
  await expect(page.getByText("草稿已保存。已发布版本保持不变。", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "发布 v1", exact: true }).click();
  await expect(page.getByText("版本 v1 已发布到用户工作台。", { exact: true })).toBeVisible();

  await page.goto("/assistant/tools");
  await expect(page.getByText(name, { exact: true })).toBeVisible();
  await page.screenshot({
    path: screenshotPath(testInfo, "workspace-published-capability"),
    animations: "disabled",
  });
  const menu = await openAccountMenu(page);
  await expect(menu.getByRole("menuitem", { name: /管理控制台/ })).toBeVisible();
  await page.screenshot({
    path: screenshotPath(testInfo, "workspace-admin-menu"),
    animations: "disabled",
  });
  await page.getByRole("button", { name: "账户菜单", exact: true }).click();

  await page.goto(detailUrl);
  await page.getByLabel("能力名称", { exact: true }).fill(versionTwo);
  await page.getByRole("button", { name: "保存草稿", exact: true }).first().click();
  await expect(page.getByText("草稿已保存。已发布版本保持不变。", { exact: true })).toBeVisible();

  await page.goto("/assistant/tools");
  await expect(page.getByText(name, { exact: true })).toBeVisible();
  await expect(page.getByText(versionTwo, { exact: true })).toHaveCount(0);

  await page.goto(detailUrl);
  await page.getByRole("button", { name: "发布 v2", exact: true }).click();
  await expect(page.getByText("版本 v2 已发布到用户工作台。", { exact: true })).toBeVisible();

  await page.goto("/assistant/tools");
  await expect(page.getByText(versionTwo, { exact: true })).toBeVisible();

  await page.goto(detailUrl);
  await page.getByRole("button", { name: "停用能力", exact: true }).click();
  const confirm = page.getByRole("dialog").filter({ hasText: "停用“" });
  await confirm.getByRole("button", { name: "确认停用", exact: true }).click();
  await expect(
    page.getByText("能力已停用；新的用户目录和新调用将不再包含该能力。", {
      exact: true,
    }),
  ).toBeVisible();

  await page.goto("/assistant/tools");
  await expect(page.getByText(versionTwo, { exact: true })).toHaveCount(0);
});

test("ordinary anonymous users do not see the admin entry", async ({ page }) => {
  await page.goto("/assistant");
  await expect(page.getByRole("textbox", { name: "询问任何问题" })).toBeVisible();
  const menu = await openAccountMenu(page);
  await expect(menu.getByRole("menuitem", { name: /管理控制台/ })).toHaveCount(0);
  await expect(menu.getByRole("menuitem", { name: /演示设置/ })).toBeVisible();
});

test("unified admin reviews the role matrix and assigns a built-in role", async ({
  page,
}, testInfo) => {
  const origin = testInfo.project.use.baseURL ?? "http://127.0.0.1:3100";
  const { password: adminPassword } = credentials(testInfo);
  await page.goto("/assistant/login?next=/assistant/admin/roles");
  await page.getByLabel("数字账号", { exact: true }).fill("1");
  await page.getByLabel("密码", { exact: true }).fill(adminPassword);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(page).toHaveURL(/\/assistant\/admin\/roles$/);
  await expect(page.getByRole("heading", { name: "角色管理", exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: "内置角色权限矩阵" })).toBeVisible();
  await expect(page.getByRole("link", { name: "用户管理", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "角色管理", exact: true })).toBeVisible();

  const rolePassword = "role-user-pass";
  const registered = await page.request.post("/api/v1/auth/register", {
    data: {
      password: rolePassword,
      passwordConfirm: rolePassword,
      nickname: "角色 E2E 用户",
    },
    headers: { origin, "Idempotency-Key": randomUUID() },
  });
  expect(registered.status()).toBe(201);
  const account = (await registered.json()).user.accountNumber as string;
  const cookies = await page.context().cookies();
  const csrf = cookies.find((item) => item.name === "paiguangguang_csrf")?.value ?? "";
  expect(csrf).not.toBe("");
  const pending = await page.request.get(`/api/v1/admin/users?q=${account}`, {
    headers: { origin },
  });
  const pendingUser = (await pending.json()).items.find(
    (item: { accountNumber: string }) => item.accountNumber === account,
  );
  expect(pendingUser).toBeTruthy();
  const activated = await page.request.post(
    `/api/v1/admin/users/${pendingUser.id}/activate`,
    {
      data: { expectedVersion: pendingUser.version, reason: "角色 E2E 激活" },
      headers: { origin, "x-csrf-token": csrf },
    },
  );
  expect(activated.status()).toBe(200);

  await page.getByLabel("搜索", { exact: true }).fill(account);
  await page.getByRole("button", { name: "查询", exact: true }).click();
  const row = page.getByRole("row").filter({ hasText: account });
  await expect(row).toBeVisible();
  page.once("dialog", (dialog) => void dialog.accept("角色 E2E 分配"));
  await row.getByLabel(`账号 ${account} 的角色`, { exact: true }).selectOption("CREATOR");
  await expect(page.getByText(`账号 ${account} 的角色已更新。`, { exact: true })).toBeVisible();
});
