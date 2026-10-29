import { defineConfig, devices } from "@playwright/test";
const database = `sqlite:////tmp/verifact-e2e-${process.pid}.db`;
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  use: { baseURL: "http://127.0.0.1:3001", trace: "retain-on-failure" },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], channel: "chrome" },
    },
  ],
  webServer: [
    {
      command:
        "../.venv/bin/alembic upgrade head && ../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001",
      cwd: "../backend",
      url: "http://127.0.0.1:8001/api/health",
      reuseExistingServer: false,
      env: {
        DATABASE_URL: database,
        FRONTEND_ORIGIN: "http://127.0.0.1:3001",
        SESSION_SECRET: "e2e-only-session-secret-32-characters-long",
      },
    },
    {
      command: "npm run dev -- --port 3001",
      url: "http://127.0.0.1:3001",
      reuseExistingServer: false,
      env: { API_BASE_URL: "http://127.0.0.1:8001", VERIFACT_E2E: "1" },
      timeout: 120000,
    },
  ],
});
