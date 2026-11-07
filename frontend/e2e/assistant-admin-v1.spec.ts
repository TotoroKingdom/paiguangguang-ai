import { expect, test, type Page, type TestInfo } from "@playwright/test";
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
