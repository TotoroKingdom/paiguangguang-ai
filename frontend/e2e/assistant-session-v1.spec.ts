import { expect, test, type Browser, type Page } from "@playwright/test";

async function waitForAssistant(page: Page) {
  await page.goto("/assistant");
  await expect(page.getByRole("textbox", { name: "询问任何问题" })).toBeVisible();
}

async function createEmptyConversation(page: Page) {
  await waitForAssistant(page);
  const open = page.getByRole("button", { name: "打开导航", exact: true });
  if (await open.isVisible()) await open.click();
  await page.getByRole("link", { name: "新建聊天", exact: true }).click();
  await expect(page).toHaveURL(/\/assistant\/chat\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { name: "今天想做点什么？" })).toBeVisible();
  return page.url();
}

async function send(page: Page, text: string) {
  const input = page.getByRole("textbox", { name: "询问任何问题" });
  await input.fill(text);
  await page.getByRole("button", { name: "发送消息", exact: true }).click();
  await expect(page.getByRole("article", { name: "用户消息", exact: true }).last()).toContainText(text);
}

test.describe("assistant server sessions", () => {
  test("creates an empty server session, persists its turn through refresh, renames, and deletes", async ({ page }) => {
    const conversationUrl = await createEmptyConversation(page);
    await send(page, "服务端持久化验收");
    await expect(page.getByRole("article", { name: "助手消息", exact: true }).last()).toContainText(
      "验证结果。",
    );

    await page.reload();
    await expect(page.getByRole("article", { name: "用户消息", exact: true }).last()).toContainText(
      "服务端持久化验收",
    );
    await expect(page.getByRole("article", { name: "助手消息", exact: true }).last()).toContainText(
      "验证结果。",
    );

    await page.getByRole("button", { name: "管理当前聊天", exact: true }).click();
    await page.getByLabel("聊天名称", { exact: true }).fill("持久化后的聊天");
    await page.getByRole("button", { name: "保存名称", exact: true }).click();
    await expect(page.getByRole("heading", { name: "持久化后的聊天" })).toBeVisible();

    await page.getByRole("button", { name: "管理当前聊天", exact: true }).click();
    await page.getByRole("button", { name: "删除这条聊天", exact: true }).click();
    await expect(page).toHaveURL(/\/assistant$/);
    await page.goto(conversationUrl);
    await expect(page.getByRole("heading", { name: "找不到这条聊天" })).toBeVisible();
  });

  test("persists stop and retry state without duplicating the user turn", async ({ page }) => {
    await createEmptyConversation(page);
    const originalUsers = await page.getByRole("article", { name: "用户消息", exact: true }).count();
    await send(page, "停止后重试");
    await page.getByRole("button", { name: "停止生成", exact: true }).click();
    await expect(page.getByText("已停止生成", { exact: true })).toBeVisible();

    await page.reload();
    await expect(page.getByText("已停止生成", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "重新生成回复", exact: true }).click();
    await expect(page.getByRole("button", { name: "发送消息", exact: true })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("article", { name: "用户消息", exact: true })).toHaveCount(originalUsers + 1);
    await expect(page.getByRole("article", { name: "助手消息", exact: true }).last()).toContainText(
      "验证结果。",
    );
  });

  test("isolates sessions between two browser contexts", async ({ browser }: { browser: Browser }) => {
    const firstContext = await browser.newContext();
    const firstPage = await firstContext.newPage();
    const conversationUrl = await createEmptyConversation(firstPage);
    await send(firstPage, "只属于第一个浏览器");

    const secondContext = await browser.newContext();
    const secondPage = await secondContext.newPage();
    await secondPage.goto(conversationUrl);
    await expect(secondPage.getByRole("heading", { name: "找不到这条聊天" })).toBeVisible();
    await expect(
      secondPage.getByText("这条记录可能已删除，或属于另一个浏览器。", { exact: true }),
    ).toBeVisible();

    await firstContext.close();
    await secondContext.close();
  });
});

