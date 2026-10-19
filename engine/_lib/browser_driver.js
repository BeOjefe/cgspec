// CGSpec browser driver. Reads a JSON job on stdin, drives Chromium through the project's
// Playwright, prints one JSON result on stdout. Never writes outside the screenshot folder.
"use strict";
const fs = require("fs");
const path = require("path");

let pw = null;
for (const name of ["playwright", "@playwright/test", "playwright-core"]) {
  try { pw = require(name); break; } catch (e) { /* try the next package */ }
}
const VIEWPORTS = {
  desktop: { viewport: { width: 1440, height: 900 } },
  mobile: { viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true },
};
const TIMEOUT = 5000;
const byId = (page, id) => page.locator(`[data-testid="${String(id).replace(/"/g, '\\"')}"]`);

async function poll(check, describe) {
  const end = Date.now() + TIMEOUT;
  let last = "";
  for (;;) {
    const [ok, seen] = await check();
    if (ok) return;
    last = seen;
    if (Date.now() > end) throw new Error(`${describe} (saw ${last})`);
    await new Promise((r) => setTimeout(r, 100));
  }
}

async function assertOne(page, a) {
  if (a.visible !== undefined) return byId(page, a.visible).first().waitFor({ state: "visible", timeout: TIMEOUT });
  if (a.hidden !== undefined) return byId(page, a.hidden).first().waitFor({ state: "hidden", timeout: TIMEOUT });
  if (a.text !== undefined) {
    return poll(async () => {
      const t = ((await byId(page, a.text).first().textContent({ timeout: TIMEOUT })) || "").trim();
      return [a.equals !== undefined ? t === String(a.equals) : t.includes(String(a.contains)), JSON.stringify(t)];
    }, `text of ${a.text} ${a.equals !== undefined ? "equals " + JSON.stringify(a.equals) : "contains " + JSON.stringify(a.contains)}`);
  }
  if (a.value !== undefined) {
    return poll(async () => {
      const v = await byId(page, a.value).first().inputValue({ timeout: TIMEOUT });
      return [v === String(a.equals), JSON.stringify(v)];
    }, `value of ${a.value} equals ${JSON.stringify(a.equals)}`);
  }
  if (a.count !== undefined) {
    return poll(async () => {
      const n = await byId(page, a.count).count();
      return [n === Number(a.equals), String(n)];
    }, `count of ${a.count} equals ${a.equals}`);
  }
  if (a.enabled !== undefined || a.disabled !== undefined) {
    const id = a.enabled !== undefined ? a.enabled : a.disabled;
    return poll(async () => {
      const on = await byId(page, id).first().isEnabled({ timeout: TIMEOUT });
      return [on === (a.enabled !== undefined), on ? "enabled" : "disabled"];
    }, `${id} is ${a.enabled !== undefined ? "enabled" : "disabled"}`);
  }
  if (a.url !== undefined) return poll(async () => [page.url().includes(a.url), page.url()], `url contains ${a.url}`);
  throw new Error(`unknown assertion ${JSON.stringify(a)}`);
}

async function step(page, s, shots, label) {
  if (s.goto !== undefined) return page.goto(s.goto, { waitUntil: "load" });
  if (s.click !== undefined) return byId(page, s.click).first().click({ timeout: TIMEOUT });
  if (s.fill !== undefined) return byId(page, s.fill).first().fill(String(s.value), { timeout: TIMEOUT });
  if (s.press !== undefined) return byId(page, s.press).first().press(s.key, { timeout: TIMEOUT });
  if (s.select !== undefined) return byId(page, s.select).first().selectOption(String(s.value), { timeout: TIMEOUT });
  if (s.check !== undefined) return byId(page, s.check).first().check({ timeout: TIMEOUT });
  if (s.hover !== undefined) return byId(page, s.hover).first().hover({ timeout: TIMEOUT });
  if (s.expect !== undefined) { for (const a of s.expect) await assertOne(page, a); return; }
  if (s.screenshot !== undefined) return page.screenshot({ path: path.join(shots, `${label}-${s.screenshot}.png`), fullPage: true });
  if (s.state !== undefined) return;
  throw new Error(`unknown step ${JSON.stringify(s)}`);
}

async function withPage(browser, viewport, fn) {
  const context = await browser.newContext(VIEWPORTS[viewport] || VIEWPORTS.desktop);
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(`page error: ${e.message}`));
  page.on("console", (m) => { if (m.type() === "error") errors.push(`console error: ${m.text()}`); });
  try { return await fn(page, errors); } finally { await context.close(); }
}

async function journey(browser, run, shots) {
  const out = [];
  for (const viewport of run.viewports) {
    const label = `${run.label}-${viewport}`;
    out.push(await withPage(browser, viewport, async (page, errors) => {
      let state = "start";
      await page.goto(run.url, { waitUntil: "load" });
      for (let i = 0; i < run.steps.length; i++) {
        const s = run.steps[i];
        if (s.state !== undefined) state = s.state;
        try { await step(page, s, shots, label); } catch (e) {
          return { viewport, ok: false, step: i, state, error: String(e.message).split("\n")[0], errors };
        }
      }
      return { viewport, ok: errors.length === 0, state, errors };
    }));
  }
  return { label: run.label, viewports: out };
}

async function audit(browser, run, shots) {
  const out = [];
  for (const viewport of ["desktop", "mobile"]) {
    out.push(await withPage(browser, viewport, async (page, errors) => {
      await page.goto(run.url, { waitUntil: "load" });
      const facts = await page.evaluate((mobile) => {
        const doc = document.documentElement;
        const small = [];
        if (mobile) {
          for (const el of document.querySelectorAll("button, a[href], input, select, textarea, [role=button]")) {
            const r = el.getBoundingClientRect();
            if (r.width > 0 && r.height > 0 && (r.width < 44 || r.height < 44)) {
              small.push(el.getAttribute("data-testid") || el.textContent.trim().slice(0, 30) || el.tagName.toLowerCase());
            }
          }
        }
        return { overflow: doc.scrollWidth > doc.clientWidth + 1, scrollWidth: doc.scrollWidth, width: doc.clientWidth,
                 small: small.slice(0, 10), smallCount: small.length };
      }, viewport === "mobile");
      await page.screenshot({ path: path.join(shots, `${run.label}-${viewport}.png`), fullPage: true });
      return { viewport, errors, ...facts };
    }));
  }
  return { label: run.label, viewports: out };
}

async function main() {
  const job = JSON.parse(fs.readFileSync(0, "utf8"));
  if (!pw) {
    console.log(JSON.stringify({ blocked: "Playwright is not installed for this project (npm i -D @playwright/test, then npx playwright install chromium)" }));
    return;
  }
  let browser;
  try {
    browser = await pw.chromium.launch(job.executable ? { executablePath: job.executable } : {});
  } catch (e) {
    console.log(JSON.stringify({ blocked: `Chromium could not start: ${String(e.message).split("\n")[0]}` }));
    return;
  }
  const results = [];
  try {
    for (const run of job.runs) results.push(await (run.kind === "audit" ? audit : journey)(browser, run, job.shots));
  } finally {
    await browser.close();
  }
  console.log(JSON.stringify({ results }));
}

main().catch((e) => { console.log(JSON.stringify({ error: String(e && e.stack || e) })); process.exit(3); });
