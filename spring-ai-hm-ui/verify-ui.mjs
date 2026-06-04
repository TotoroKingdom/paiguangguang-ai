import { chromium } from "playwright";

const BASE_URL = "http://localhost:3000";

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function screenshot(page, name) {
  await page.screenshot({ path: `verify-${name}.png`, fullPage: false });
  console.log(`📸 Screenshot: verify-${name}.png`);
}

const browser = await chromium.launch({
  headless: true,
  executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
});
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await context.newPage();

console.log("=== Verification Script ===\n");

// 1. Load page
console.log("1. Loading page...");
await page.goto(BASE_URL);
await sleep(2000);
await screenshot(page, "01-initial");

const welcomeVisible = await page.isVisible("text=How can I help?");
console.log(welcomeVisible ? "✅ Welcome message visible (no mock data)" : "❌ Welcome message NOT visible");

// 2. Send a message (backend is likely down, so we'll get an error)
console.log("\n2. Sending message...");
await page.fill("textarea", "你是谁");
await sleep(200);
await page.click('button[aria-label="Send message"]');
await sleep(1500);
await screenshot(page, "02-after-send");

const userMessageVisible = await page.isVisible("text=你是谁");
console.log(userMessageVisible ? "✅ User message visible" : "❌ User message NOT visible");

// Wait a bit for error (backend down)
await sleep(4000);
await screenshot(page, "03-error-or-stopped");

const assistantVisible = await page.locator("article").count() > 1;
console.log(assistantVisible ? "✅ Assistant message appeared" : "❌ Assistant message did NOT appear");

// 3. Test new chat
console.log("\n3. Creating new chat...");
await page.click("text=New chat");
await sleep(1000);
await screenshot(page, "04-new-chat");

const newChatWelcome = await page.isVisible("text=How can I help?");
console.log(newChatWelcome ? "✅ New chat shows welcome" : "❌ New chat does NOT show welcome");

// 4. Send markdown message
console.log("\n4. Sending markdown message...");
await page.fill("textarea", "Show me **bold**, `code`, and a list:\n- Item 1\n- Item 2");
await sleep(200);
await page.click('button[aria-label="Send message"]');
await sleep(1500);
await screenshot(page, "05-markdown");

const boldVisible = await page.isVisible("strong:has-text('bold')");
const codeVisible = await page.isVisible("code:has-text('code')");
const listVisible = await page.isVisible("li:has-text('Item 1')");
console.log(boldVisible ? "✅ Bold rendering works" : "❌ Bold rendering broken");
console.log(codeVisible ? "✅ Inline code rendering works" : "❌ Inline code rendering broken");
console.log(listVisible ? "✅ List rendering works" : "❌ List rendering broken");

// 5. Refresh and check persistence
console.log("\n5. Refreshing page...");
await page.reload();
await sleep(2000);
await screenshot(page, "06-after-refresh");

const persistedMessages = await page.locator("article").count();
console.log(persistedMessages > 0 ? `✅ Messages persisted (${persistedMessages} messages)` : "❌ Messages NOT persisted");

// 6. Switch conversations
console.log("\n6. Testing conversation switch...");
// Sidebar should show multiple conversations now. Click the first one (the "你是谁" conversation)
const convButtons = await page.locator("aside .space-y-1 > button").all();
if (convButtons.length >= 2) {
  // Click the second conversation (the "你是谁" one)
  await convButtons[1].click();
  await sleep(1000);
  await screenshot(page, "07-switch-conv");

  const switchedToFirst = await page.isVisible("text=你是谁");
  console.log(switchedToFirst ? "✅ Conversation switching works" : "❌ Conversation switching broken");

  // Switch back to the markdown conversation (first one)
  await convButtons[0].click();
  await sleep(1000);
  await screenshot(page, "08-switch-back");

  const switchedBack = await page.isVisible("text=Show me");
  console.log(switchedBack ? "✅ Switch back to second conversation works" : "❌ Switch back broken");
} else {
  console.log("⚠️ Not enough conversations in sidebar to test switching");
}

console.log("\n=== Verification Complete ===");
await browser.close();
