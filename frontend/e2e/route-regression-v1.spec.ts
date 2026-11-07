import { expect, test } from "@playwright/test";

const routes = [
  "/",
  "/rag",
  "/lab/3d",
  "/threejs",
  "/assistant",
  "/assistant/tools",
  "/assistant/skills",
  "/assistant/mcp",
  "/assistant/agents",
  "/assistant/files",
];

for (const route of routes) {
  test(`route remains available: ${route}`, async ({ page }) => {
    const response = await page.goto(route);
    expect(response?.status()).toBeLessThan(400);
    await expect(page.locator("main")).toBeVisible();
    await expect(page.locator("body")).not.toContainText("This page could not be found");
  });
}
