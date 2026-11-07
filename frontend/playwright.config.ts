import { chromium, defineConfig } from "@playwright/test";
import { randomBytes } from "node:crypto";
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
const pythonExecutable = process.platform === "win32"
  ? ".venv/Scripts/python.exe"
  : ".venv/bin/python";
const venvPython = [
  path.join(backendRoot, pythonExecutable),
  path.resolve(process.cwd(), "..", pythonExecutable),
].find((candidate) => existsSync(candidate));
const python = venvPython ? `"${venvPython}"` : "python";
const databasePath = path.join(os.tmpdir(), `paiguangguang-assistant-playwright-${process.pid}.db`);
const databaseUrl = `sqlite:///${databasePath.replaceAll("\\", "/")}`;
const adminUsername = process.env.ASSISTANT_ADMIN_USERNAME ?? "e2e-admin";
const adminPassword =
  process.env.ASSISTANT_ADMIN_PASSWORD ?? randomBytes(24).toString("base64url");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  reporter: [["list"], ["html", { open: "never" }]],
  metadata: { adminUsername, adminPassword },
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
        ASSISTANT_ADMIN_USERNAME: adminUsername,
        ASSISTANT_ADMIN_PASSWORD: adminPassword,
        ASSISTANT_ADMIN_COOKIE_SECURE: "false",
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
