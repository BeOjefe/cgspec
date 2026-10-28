import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

test('real browser click increments the count', async ({ page }) => {
  const source = readFileSync('src/widget.js', 'utf8');
  await page.setContent('<button id="count">0</button>');
  await page.addScriptTag({ type: 'module', content: `${source}\nwindow.countAfterClick = countAfterClick;` });
  await page.waitForFunction(() => typeof window.countAfterClick === 'function');
  await page.getByRole('button', { name: '0' }).click();
  await page.evaluate(() => {
    const button = document.querySelector('#count');
    button.textContent = String(window.countAfterClick(Number(button.textContent)));
  });
  await expect(page.getByRole('button', { name: '1' })).toBeVisible();
});
