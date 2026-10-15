import { defineConfig } from "@playwright/test";

// The tests run against the static export (STATIC_EXPORT=1 npm run build) with the API mocked,
// so they need no backend, database or LLM key.
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["list"]] : "list",
  use: { baseURL: "http://127.0.0.1:4173", viewport: { width: 1440, height: 900 } },
  webServer: {
    command: "node e2e/serve.mjs",
    url: "http://127.0.0.1:4173/login/",
    reuseExistingServer: !process.env.CI,
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
