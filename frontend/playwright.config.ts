import { chromium, defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";
import path from "node:path";

const chromePaths = [
  path.join(
    process.env.PROGRAMFILES ?? "C:\\Program Files",
    "Google/Chrome/Application/chrome.exe",
  ),
  path.join(process.env.LOCALAPPDATA ?? "", "Google/Chrome/Application/chrome.exe"),
];
// Prefer Playwright Chromium; use an installed Chrome on Windows if its download is unavailable.
const channel =
  process.env.PLAYWRIGHT_CHANNEL ??
  (!existsSync(chromium.executablePath()) &&
  process.platform === "win32" &&
  chromePaths.some((file) => existsSync(file))
    ? "chrome"
    : undefined);

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    channel,
    baseURL: "http://127.0.0.1:3100",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop", use: { browserName: "chromium", viewport: { width: 1440, height: 1000 } } },
    {
      name: "mobile",
      use: {
        browserName: "chromium",
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
  webServer: {
    command: "npm run dev -- --hostname 127.0.0.1 --port 3100",
    url: "http://127.0.0.1:3100/assistant",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
