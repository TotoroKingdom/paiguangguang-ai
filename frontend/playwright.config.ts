import { chromium, defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";
import os from "node:os";
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

const port = Number(process.env.PLAYWRIGHT_PORT ?? 3100);
const backendPort = Number(process.env.PLAYWRIGHT_BACKEND_PORT ?? 8001);
const backendRoot = path.resolve(process.cwd(), "../backend");
const venvPython = path.join(
  backendRoot,
  process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python",
);
const python = existsSync(venvPython) ? `"${venvPython}"` : "python";
const databasePath = path.join(os.tmpdir(), `paiguangguang-assistant-playwright-${process.pid}.db`);
const databaseUrl = `sqlite:///${databasePath.replaceAll("\\", "/")}`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    channel,
    baseURL: `http://127.0.0.1:${port}`,
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
  webServer: [
    {
      command: `${python} -m uvicorn app.main:app --host 127.0.0.1 --port ${backendPort}`,
      cwd: backendRoot,
      url: `http://127.0.0.1:${backendPort}/api/v1/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ...process.env,
        ASSISTANT_DATABASE_URL: databaseUrl,
        ASSISTANT_ENVIRONMENT: "development",
        ASSISTANT_OWNER_COOKIE_SECRET: "playwright-assistant-owner-secret-32-characters",
      },
    },
    {
      command: `npx next dev --hostname 127.0.0.1 --port ${port}`,
      cwd: process.cwd(),
      url: `http://127.0.0.1:${port}/assistant`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ...process.env,
        ASSISTANT_API_INTERNAL_URL: `http://127.0.0.1:${backendPort}`,
      },
    },
  ],
});
