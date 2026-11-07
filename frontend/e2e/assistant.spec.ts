import { test, expect, type Page } from "@playwright/test";
import path from "node:path";

const storageKey = "paiguangguang.assistant.v1";
const localStorageKey = "paiguangguang.assistant.local.v1";
let pageErrors: string[] = [];
let externalRequests: string[] = [];
test.beforeEach(async ({ page }) => {
  pageErrors = [];
  externalRequests = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("request", (request) => {
    if (/^https?:/.test(request.url()) && !request.url().startsWith(`http://127.0.0.1:${process.env.PLAYWRIGHT_PORT ?? 3100}/`))
      externalRequests.push(request.url());
  });
});
test.afterEach(async () => {
  expect(pageErrors, "No browser runtime or hydration errors").toEqual([]);
  expect(externalRequests, "Prototype does not call external services").toEqual([]);
});
async function ready(page: Page, route = "/assistant") {
  await page.goto(route);
  await expect(page.getByRole("textbox", { name: "询问任何问题" })).toBeVisible();
}
async function navigate(page: Page, name: string) {
  const open = page.getByRole("button", { name: "打开导航", exact: true });
  if (await open.isVisible()) await open.click();
  await page
    .getByRole("navigation", { name: "助手导航" })
    .getByRole("link", { name, exact: true })
    .click();
}
async function chooseCapability(page: Page, name: string) {
  await page
    .getByRole("main")
    .getByRole("button")
    .filter({ has: page.locator("strong", { hasText: name }) })
    .first()
    .click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: "用于聊天", exact: true }).click();
}
async function send(page: Page, text: string) {
  await page.getByRole("textbox", { name: "询问任何问题" }).fill(text);
  await page.getByRole("button", { name: "发送消息", exact: true }).click();
  await expect(page).toHaveURL(/\/assistant\/chat\//);
  const reply = page.getByRole("article", { name: "助手消息", exact: true }).last();
  await expect(reply).toBeVisible();
  await expect(reply.locator(".as-message-status")).toHaveCount(0);
}
async function createConversation(page: Page) {
  await ready(page);
  const open = page.getByRole("button", { name: "打开导航", exact: true });
  if (await open.isVisible()) await open.click();
  await page.getByRole("link", { name: "新建聊天", exact: true }).click();
  await expect(page).toHaveURL(/\/assistant\/chat\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { name: "今天想做点什么？" })).toBeVisible();
  return page.url();
}

test("homepage aligns V2, preserves anchors, and opens the assistant card by keyboard", async ({
  page,
}) => {
  await page.goto("/");
  const capabilities = page.getByRole("region", { name: "我的技术栈" });
  await expect(capabilities.getByRole("article")).toHaveCount(4);
  await expect(capabilities).toContainText("Supervisor");
  await expect(capabilities).toContainText("ReAct");
  await expect(capabilities).toContainText("MySQL / PostgreSQL");
  const exploration = page.getByRole("region", { name: "我正在探索的项目" });
  await expect(exploration.getByRole("article")).toHaveCount(5);
  await expect(exploration).not.toContainText("OpenClaw");
  const journey = page.getByRole("region", { name: "我的职业生涯规划" });
  await expect(journey.locator("ol > li")).toHaveCount(4);
  await expect(journey).toContainText("FDE");
  for (const id of ["hero", "capabilities", "projects", "building", "exploring", "journey"])
    await expect(page.locator(`#${id}`)).toHaveCount(1);
  const assistant = page.getByRole("link", { name: /智能助手.*体验原型/ });
  await assistant.focus();
  await assistant.press("Enter");
  await expect(page).toHaveURL(/\/assistant$/);
  await expect(page.getByRole("heading", { name: "今天想做点什么？" })).toBeVisible();
  const returnLink = page.getByRole("link", { name: "返回网站", exact: true });
  if (!(await returnLink.isVisible())) await page.getByRole("button", { name: "打开导航" }).click();
  await returnLink.click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto("/rag");
  await expect(page.getByRole("main")).toBeVisible();
});

for (const scenario of [
  {
    route: "/assistant/tools",
    name: "网页搜索",
    query: "查一下最近一周的 AI Agent 新闻",
    step: "调用参数",
  },
  {
    route: "/assistant/skills",
    name: "PRD编写",
    query: "请编写智能助手的产品需求",
    step: "整理验收标准",
  },
  {
    route: "/assistant/mcp",
    name: "知识中心MCP",
    query: "查询最近一周的知识治理任务",
    step: "连接",
  },
  {
    route: "/assistant/agents",
    name: "知识分析师",
    query: "分析知识治理中的主要问题",
    step: "制定计划",
  },
]) {
  test(`${scenario.name}: select capability, simulate task, refresh history and navigate back`, async ({
    page,
  }) => {
    await ready(page, scenario.route);
    await chooseCapability(page, scenario.name);
    await expect(page.locator(".as-draft-chip--capability")).toContainText(scenario.name);
    await send(page, scenario.query);
    const idUrl = page.url();
    const reply = page.getByRole("article", { name: "助手消息", exact: true }).last();
    await expect(reply).toContainText(scenario.step);
    await expect(reply.locator(".as-markdown")).not.toBeEmpty();
    await page.reload();
    await expect(page.getByRole("article", { name: "用户消息" }).last()).toContainText(
      scenario.query,
    );
    await navigate(page, "工具 Tool");
    await expect(page).toHaveURL(/\/assistant\/tools$/);
    await page.goBack();
    await expect(page).toHaveURL(idUrl);
    await expect(page.getByRole("article", { name: "助手消息" }).last()).toContainText(
      scenario.step,
    );
    await page.goForward();
    await expect(page).toHaveURL(/\/assistant\/tools$/);
  });
}

test("catalog filters and favorites persist, and @ searches all kinds", async ({ page }) => {
  await ready(page, "/assistant/tools");
  const main = page.getByRole("main");
  await main.getByRole("textbox", { name: "搜索工具" }).fill("SQL");
  await expect(main.getByRole("article")).toHaveCount(1);
  await main.getByRole("button", { name: "添加常用：SQL查询" }).click();
  await page.reload();
  await expect(main.getByRole("button", { name: "移出常用：SQL查询" })).toBeVisible();
  await main.getByRole("textbox", { name: "搜索工具" }).fill("");
  await main.getByRole("button", { name: "信息检索", exact: true }).click();
  await expect(main.getByRole("article")).toHaveCount(1);
  await main.getByRole("button", { name: "全部", exact: true }).click();
  await page.getByRole("textbox", { name: "询问任何问题" }).fill("@PRD");
  await page.getByRole("option", { name: /PRD编写/ }).click();
  await expect(page.locator(".as-draft-chip--capability")).toContainText("PRD编写");
  await expect(page.getByRole("textbox", { name: "询问任何问题" })).toHaveValue("");
});

test("skills import markdown, expose its text, persist and delete with confirmation", async ({
  page,
}) => {
  await ready(page, "/assistant/skills");
  await page
    .getByLabel("导入技能文件")
    .setInputFiles({
      name: "analysis.md",
      mimeType: "text/markdown",
      buffer: Buffer.from("# 我的研究技能\n\n先收集证据，再交叉验证并给出结论。"),
    });
  await expect(page.getByRole("main")).toContainText("我的研究技能");
  await page.reload();
  await chooseCapability(page, "我的研究技能");
  await expect(page.locator(".as-draft-chip--capability")).toContainText("我的研究技能");
  await page
    .getByRole("main")
    .getByRole("button")
    .filter({ has: page.locator("strong", { hasText: "我的研究技能" }) })
    .click();
  await expect(page.getByRole("dialog")).toContainText("先收集证据");
  await page.getByRole("button", { name: "删除技能", exact: true }).click();
  await page.getByRole("dialog").getByRole("button", { name: "确认删除", exact: true }).click();
  await expect(page.getByRole("main").getByText("我的研究技能", { exact: true })).toHaveCount(0);
  await expect(page.locator(".as-draft-chip--capability")).toHaveCount(0);
});

test("connector guards chat, validates configuration, simulates failure, retries and disconnects", async ({
  page,
}) => {
  await ready(page, "/assistant/mcp");
  await chooseCapability(page, "数据库MCP");
  await page.getByRole("textbox", { name: "询问任何问题" }).fill("查询任务表");
  await page.getByRole("button", { name: "发送消息" }).click();
  await expect(page.locator(".as-composer").getByRole("alert")).toContainText("尚未完成模拟连接");
  await page
    .getByRole("main")
    .getByRole("button")
    .filter({ has: page.locator("strong", { hasText: "数据库MCP" }) })
    .click();
  await page.getByRole("dialog").getByRole("button", { name: "连接设置", exact: true }).click();
  await page.getByLabel("连接地址", { exact: true }).fill("wrong");
  await page.getByRole("button", { name: "保存配置" }).click();
  await expect(page.getByRole("dialog").getByRole("alert")).toBeVisible();
  await page.getByLabel("连接地址", { exact: true }).fill("https://database.example.invalid/mcp");
  await page.getByRole("button", { name: "保存配置" }).click();
  await page
    .getByRole("main")
    .getByRole("button")
    .filter({ has: page.locator("strong", { hasText: "数据库MCP" }) })
    .click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("模拟连接失败", { exact: true }).check();
  await dialog.getByRole("button", { name: "测试连接", exact: true }).click();
  await expect(dialog.getByRole("alert")).toContainText("模拟连接失败");
  await dialog.getByLabel("模拟连接失败", { exact: true }).uncheck();
  await dialog.getByRole("button", { name: "重试连接", exact: true }).click();
  await expect(dialog.getByText("状态：已连接", { exact: true })).toBeVisible();
  await dialog.getByRole("button", { name: "断开连接", exact: true }).click();
  await expect(dialog.getByText("状态：已断开", { exact: true })).toBeVisible();
  await page.keyboard.press("Escape");
  await page.reload();
  await page
    .getByRole("main")
    .getByRole("button")
    .filter({ has: page.locator("strong", { hasText: "数据库MCP" }) })
    .click();
  await expect(page.getByRole("dialog").getByText("状态：已断开", { exact: true })).toBeVisible();
});

test("file metadata uploads and multiple attachments survive refresh and deletion", async ({
  page,
}) => {
  await ready(page, "/assistant/files");
  await page.getByLabel("上传本地文件").setInputFiles([
    {
      name: "演示需求.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("不可用作真实正文的演示内容"),
    },
    { name: "季度数据.csv", mimeType: "text/csv", buffer: Buffer.from("month,total\n1,10") },
  ]);
  await page.reload();
  await expect(page.getByRole("main")).toContainText("演示需求.txt");
  await page.getByRole("main").getByRole("button", { name: "选择聊天附件" }).click();
  await page
    .getByRole("dialog")
    .getByLabel(/演示需求.txt/)
    .check();
  await page
    .getByRole("dialog")
    .getByLabel(/季度数据.csv/)
    .check();
  await page.getByRole("dialog").getByRole("button", { name: "用于聊天" }).click();
  await send(page, "请整理附件的元信息");
  const reply = page.getByRole("article", { name: "助手消息" }).last();
  await expect(reply).toContainText("演示需求.txt");
  await expect(reply).toContainText("季度数据.csv");
  const conversationUrl = page.url();
  await navigate(page, "文件库");
  await page.getByRole("button", { name: "删除文件：演示需求.txt", exact: true }).click();
  await page.getByRole("dialog").getByRole("button", { name: "确认删除" }).click();
  await page.goto(conversationUrl);
  await expect(page.getByRole("article", { name: "用户消息" }).last()).toContainText(
    "演示需求.txt",
  );
});

test("stop, regenerate, simulate failure and retry without duplicating user messages", async ({
  page,
}) => {
  await createConversation(page);
  const originalUsers = await page.getByRole("article", { name: "用户消息" }).count();
  await page.getByRole("textbox", { name: "询问任何问题" }).fill("测试停止生成");
  await page.getByRole("button", { name: "发送消息" }).click();
  await page.getByRole("button", { name: "停止生成", exact: true }).click();
  await expect(page.getByText("已停止生成", { exact: true })).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "重新生成回复" }).click();
  await expect(page.getByRole("button", { name: "发送消息" })).toBeVisible();
  await expect(page.getByRole("article", { name: "用户消息" })).toHaveCount(originalUsers + 1);
  await page.getByRole("button", { name: "演示场景", exact: true }).click();
  await page.getByLabel("模拟生成失败", { exact: true }).check();
  await page.getByRole("button", { name: "应用场景" }).click();
  await page.getByRole("textbox", { name: "询问任何问题" }).fill("体验失败重试");
  await page.getByRole("button", { name: "发送消息" }).click();
  await page.getByRole("button", { name: "重试回复" }).click();
  await expect(page.getByRole("button", { name: "发送消息" })).toBeVisible();
  await expect(page.getByRole("article", { name: "用户消息" })).toHaveCount(originalUsers + 2);
});

test("drafts remain isolated between conversations and new-chat pages", async ({ page }) => {
  const firstConversation = await createConversation(page);
  await page.getByRole("textbox", { name: "询问任何问题" }).fill("会话一未发送草稿");
  await page.goto("/assistant");
  const open = page.getByRole("button", { name: "打开导航", exact: true });
  if (await open.isVisible()) await open.click();
  await page
    .getByRole("navigation", { name: "助手导航" })
    .getByRole("link", { name: "新建聊天", exact: true })
    .click();
  await expect(page).toHaveURL(/\/assistant\/chat\/[0-9a-f-]{36}$/);
  const secondConversation = page.url();
  expect(secondConversation).not.toBe(firstConversation);
  await expect(page.getByRole("textbox", { name: "询问任何问题" })).toHaveValue("");
  await expect(page.getByRole("textbox", { name: "询问任何问题" })).toHaveValue("");
  await page.getByRole("textbox", { name: "询问任何问题" }).fill("新聊天草稿");
  await page.goto(firstConversation);
  await expect(page.getByRole("textbox", { name: "询问任何问题" })).toHaveValue("会话一未发送草稿");
  await page.goto(secondConversation);
  await expect(page.getByRole("textbox", { name: "询问任何问题" })).toHaveValue("新聊天草稿");
});

test("conversation search, rename, missing route and confirmed reset", async ({ page }) => {
  await createConversation(page);
  await send(page, "用于重命名的消息");
  await page.getByRole("button", { name: "管理当前聊天" }).click();
  await page.getByLabel("聊天名称", { exact: true }).fill("重命名后的研究");
  await page.getByRole("button", { name: "保存名称" }).click();
  await page.reload();
  await expect(page.getByRole("heading", { name: "重命名后的研究" })).toBeVisible();
  const menu = page.getByRole("button", { name: "打开导航", exact: true });
  if (await menu.isVisible()) await menu.click();
  await page.getByRole("button", { name: "搜索聊天", exact: true }).click();
  await page.getByLabel("聊天名称", { exact: true }).fill("重命名");
  await expect(page.getByRole("dialog").getByRole("link")).toHaveCount(1);
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "管理当前聊天" }).click();
  await page.getByRole("button", { name: "删除这条聊天" }).click();
  await expect(page).toHaveURL(/\/assistant$/);
  for (const id of ["missing", "constructor", "toString"]) {
    await page.goto(`/assistant/chat/${id}`);
    await expect(page.getByRole("heading", { name: "找不到这条聊天" })).toBeVisible();
  }
  if (await menu.isVisible()) await menu.click();
  await page.getByRole("button", { name: "演示设置" }).click();
  await page.getByRole("button", { name: "重置演示数据", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "重置演示数据" });
  await expect(dialog).toBeVisible();
  await page.keyboard.press("Tab");
  expect(await dialog.evaluate((el) => el.contains(document.activeElement))).toBeTruthy();
  await dialog.getByRole("button", { name: "确认重置" }).click();
  await expect(page).toHaveURL(/\/assistant$/);
  await page.reload();
  const state = await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!), localStorageKey);
  expect(state.conversations).toHaveLength(0);
  expect(state.userSkills).toHaveLength(0);
  expect(state.files).toHaveLength(3);
});

test("invalid storage recovers and unavailable storage keeps the prototype usable", async ({
  page,
}) => {
  await page.addInitScript((key) => {
    localStorage.setItem(key, '{"version":1,"files":"invalid"}');
  }, storageKey);
  await ready(page);
  await expect(page.getByRole("heading", { name: "今天想做点什么？" })).toBeVisible();
  expect(
    await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!).files.length, localStorageKey),
  ).toBe(3);
  await page.addInitScript(() => {
    Object.defineProperty(Storage.prototype, "getItem", {
      value: () => {
        throw new Error("Storage unavailable");
      },
    });
    Object.defineProperty(Storage.prototype, "setItem", {
      value: () => {
        throw new Error("Storage unavailable");
      },
    });
  });
  await page.reload();
    await expect(page.getByRole("status")).toContainText("本地配置不可用");
  await send(page, "没有本地存储仍然可以聊天");
  await expect(page.getByRole("article", { name: "助手消息" }).last()).not.toBeEmpty();
});

test("keyboard dialog and mobile drawer focus, layout and reduced motion", async ({
  page,
}, testInfo) => {
  await ready(page, "/assistant/tools");
  const manage = page.getByRole("button", { name: "管理常用", exact: true });
  await manage.click();
  await page.keyboard.press("Escape");
  await expect(manage).toBeFocused();
  if (testInfo.project.name === "mobile") {
    const toggle = page.getByRole("button", { name: "打开导航" });
    await toggle.click();
    await expect(page.getByRole("dialog", { name: "助手侧栏" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(toggle).toBeFocused();
    expect(
      await page.locator(".as-sidebar").evaluate((el) => getComputedStyle(el).visibility),
    ).toBe("hidden");
  }
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
  ).toBeTruthy();
  const lastCard = page.getByRole("main").getByRole("article").last();
  await lastCard.scrollIntoViewIfNeeded();
  const cardBox = await lastCard.boundingBox();
  const footerBox = await page.locator(".as-composer-area").boundingBox();
  expect(cardBox!.y + cardBox!.height).toBeLessThanOrEqual(footerBox!.y + 2);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/#capabilities");
  await page
    .getByRole("navigation", { name: "主导航" })
    .getByRole("link", { name: "规划", exact: true })
    .click({ force: true });
  await page.locator("#journey").scrollIntoViewIfNeeded();
  await page.locator("#hero").scrollIntoViewIfNeeded();
  await expect(page.locator("#hero")).toBeVisible();
});

test("capture desktop and mobile visual evidence", async ({ page }, testInfo) => {
  test.setTimeout(120_000);
  const directory = path.resolve(process.cwd(), "../docs-codex/homepage-v2/screenshots");
  const prefix = testInfo.project.name;
  await page.goto("/");
  await expect(page.locator(".home-page")).toHaveAttribute("data-ai-core", /ready|fallback/, {
    timeout: 30_000,
  });
  await page.screenshot({
    path: path.join(directory, `${prefix}-home-hero-normal.png`),
    animations: "disabled",
  });
  await page.emulateMedia({ reducedMotion: "reduce" });
  for (const section of ["capabilities", "projects", "journey"]) {
    await page.goto(`/#${section}`);
    await expect(page.locator(".home-page")).toHaveAttribute("data-ai-core", /ready|fallback/, {
      timeout: 30_000,
    });
    await page.locator(`#${section}`).scrollIntoViewIfNeeded();
    await page.screenshot({
      path: path.join(directory, `${prefix}-home-${section}.png`),
      animations: "disabled",
    });
  }
  await page.goto("/#capabilities");
  await expect(page.locator(".home-page")).toHaveAttribute("data-ai-core", /ready|fallback/, {
    timeout: 30_000,
  });
  await page
    .locator("#capabilities")
    .screenshot({
      path: path.join(directory, `${prefix}-home-capabilities-full.png`),
      animations: "disabled",
    });
  await page
    .getByRole("article")
    .filter({ has: page.getByRole("heading", { name: "智能助手", exact: true }) })
    .screenshot({
      path: path.join(directory, `${prefix}-home-assistant-card.png`),
      animations: "disabled",
    });
  for (const route of ["", "/tools", "/skills", "/mcp", "/agents", "/files"]) {
    await ready(page, `/assistant${route}`);
    await page.screenshot({
      path: path.join(directory, `${prefix}-assistant${route.replace("/", "-") || "-initial"}.png`),
      animations: "disabled",
    });
  }
  await navigate(page, "技能 Skill");
  await chooseCapability(page, "PRD编写");
  await send(page, "编写一个智能助手的产品需求");
  await page.screenshot({
    path: path.join(directory, `${prefix}-assistant-chat.png`),
    animations: "disabled",
  });
});


test("composer grows naturally, keeps a single focus surface, and respects keyboard input", async ({ page }, testInfo) => {
  await ready(page);
  const input = page.getByRole("textbox", { name: "询问任何问题" });
  const sendButton = page.getByRole("button", { name: "发送消息", exact: true });
  await expect(sendButton).toBeDisabled();
  await input.focus();
  await expect(input).toHaveCSS("outline-style", "none");
  await page.screenshot({ path: testInfo.outputPath("assistant-polished.png"), animations: "disabled" });
  const initialHeight = await input.evaluate((element) => element.clientHeight);
  await input.fill("第一行");
  await input.press("Shift+Enter");
  await input.press("Shift+Enter");
  await input.press("Shift+Enter");
  await input.press("Shift+Enter");
  await input.press("Shift+Enter");
  await input.press("Shift+Enter");
  await input.pressSequentially("继续整理");
  await expect(input).toHaveValue(/第一行\n/);
  expect(await input.evaluate((element) => element.clientHeight)).toBeGreaterThan(initialHeight);
  await input.fill("短问题");
  await expect.poll(() => input.evaluate((element) => element.clientHeight)).toBe(initialHeight);
  await input.press("Enter");
  await expect(page).toHaveURL(/\/assistant\/chat\//);
  await expect(page.getByRole("article", { name: "用户消息", exact: true }).last()).toContainText("短问题");
  await expect(input).toHaveValue("");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(page.locator(".as-composer")).toHaveCSS("transition-duration", "0s");
});
