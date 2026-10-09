import { defineConfig } from "@playwright/test";

// Browser end-to-end tests. Start both servers first (see README), then: npm run test:e2e
// Uses the installed Google Chrome, so no browser download is needed.
export default defineConfig({
  testDir: "e2e",
  timeout: 90_000,
  use: { baseURL: process.env.E2E_URL ?? "http://localhost:3000", channel: "chrome", trace: "retain-on-failure" },
});
