import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: '**/*.spec.js',
  use: {
    browserName: 'chromium', headless: true,
    launchOptions: process.env.CGSPEC_CHROME_PATH ? { executablePath: process.env.CGSPEC_CHROME_PATH } : {},
  },
  reporter: 'json',
});
