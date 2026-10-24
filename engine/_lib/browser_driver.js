// CGSpec browser driver. Reads a JSON job on stdin, drives Chromium through Playwright (the project's,
// or only the trusted CGSPEC_PLAYWRIGHT_DIR copy when that is set), prints one JSON result on stdout.
// Never writes outside the screenshot folder.
"use strict";
const fs = require("fs");
const path = require("path");

const PACKAGES = ["playwright", "@playwright/test", "playwright-core"];
// Trusted mode (CI): load Playwright only from CGSPEC_PLAYWRIGHT_DIR/node_modules by absolute path, so
// modules committed in the checked project can never stand in for the browser.
const TRUSTED = process.env.CGSPEC_PLAYWRIGHT_DIR || "";
function loadPlaywright() {
  for (const name of PACKAGES) {
    try {
      if (!TRUSTED) return require(name);
      const dir = path.join(TRUSTED, "node_modules", name);
      if (fs.existsSync(path.join(dir, "package.json"))) return require(dir);
    } catch (e) { /* try the next package */ }
  }
  return null;
}
const pw = loadPlaywright();
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

async function withPage(browser, viewport, fn, shots, label, video, extraOptions = {}) {
  const options = { ...(VIEWPORTS[viewport] || VIEWPORTS.desktop), ...extraOptions };
  if (video) options.recordVideo = { dir: shots, size: options.viewport };
  const context = await browser.newContext(options);
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(`page error: ${e.message}`));
  page.on("console", (m) => { if (m.type() === "error") errors.push(`console error: ${m.text()}`); });
  try { return await fn(page, errors); } finally {
    await context.close();
    if (video) {
      const videoPath = await page.video().path();
      const target = path.join(shots, `${label}.webm`);
      if (videoPath !== target) fs.copyFileSync(videoPath, target);
    }
  }
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
      // Every journey viewport leaves a final screenshot; Python requires it before a PASS.
      await page.screenshot({ path: path.join(shots, `${label}.png`), fullPage: true });
      return { viewport, ok: errors.length === 0, state, errors };
    }, shots, label, Boolean(run.video)));
  }
  return { label: run.label, viewports: out };
}

// Runs in the page: contrast of visible text, font sizes, spacing values and saturated hues in use.
function measureQuality() {
  const parse = (c) => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const v = m[1].split(/[\s,\/]+/).filter(Boolean).map(Number); return { r: v[0], g: v[1], b: v[2], a: v.length > 3 ? v[3] : 1 }; };
  const lum = (c) => { const f = (x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const blend = (top, under) => ({ r: top.r * top.a + under.r * (1 - top.a), g: top.g * top.a + under.g * (1 - top.a),
    b: top.b * top.a + under.b * (1 - top.a), a: 1 });
  const background = (el) => { const layers = [];
    for (let e = el; e; e = e.parentElement) { const st = getComputedStyle(e);
      if (st.backgroundImage && st.backgroundImage !== "none") return null;
      const c = parse(st.backgroundColor); if (c && c.a > 0) { layers.push(c); if (c.a >= 1) break; } }
    let out = { r: 255, g: 255, b: 255, a: 1 }; for (let i = layers.length - 1; i >= 0; i--) out = blend(layers[i], out); return out; };
  const hue = (c) => { const r = c.r / 255, g = c.g / 255, b = c.b / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
    const l = (mx + mn) / 2, s = d === 0 ? 0 : d / (1 - Math.abs(2 * l - 1)); if (s < 0.35 || l < 0.15 || l > 0.9) return null;
    let h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; return Math.round(((h * 60) + 360) % 360); };
  const visible = (el) => { const r = el.getBoundingClientRect(); const st = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && st.visibility !== "hidden" && st.display !== "none" && Number(st.opacity) > 0.05; };
  const fails = [], sizes = {}, spacing = {}, hues = {}; let texts = 0;
  for (const el of document.body.querySelectorAll("*")) {
    if (!visible(el)) continue;
    const st = getComputedStyle(el);
    for (const prop of ["paddingTop", "paddingRight", "paddingBottom", "paddingLeft", "marginTop", "marginBottom", "rowGap", "columnGap"]) {
      const v = parseFloat(st[prop]); if (v > 0) spacing[Math.round(v)] = (spacing[Math.round(v)] || 0) + 1; }
    for (const prop of ["backgroundColor", "color", "borderTopColor"]) {
      const c = parse(st[prop]); if (!c || c.a < 0.5) continue;
      if (prop === "borderTopColor" && parseFloat(st.borderTopWidth) === 0) continue;
      const h = hue(c); if (h !== null) { const bin = Math.round(h / 30) * 30 % 360; hues[bin] = (hues[bin] || 0) + 1; } }
    const own = Array.from(el.childNodes).some((n) => n.nodeType === 3 && n.textContent.trim());
    if (!own) continue;
    texts++;
    const size = parseFloat(st.fontSize); sizes[Math.round(size * 10) / 10] = (sizes[Math.round(size * 10) / 10] || 0) + 1;
    const fg = parse(st.color), bg = background(el); if (!fg || !bg) continue;
    const top = blend(fg, bg), a = lum(top), b = lum(bg), ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    const large = size >= 24 || (size >= 18.66 && Number(st.fontWeight) >= 700);
    if (ratio < (large ? 3 : 4.5)) fails.push({ text: el.textContent.trim().slice(0, 30), ratio: Math.round(ratio * 100) / 100,
      need: large ? 3 : 4.5, id: el.getAttribute("data-testid") || "" });
  }
  return { texts, contrastFails: fails.slice(0, 10), contrastFailCount: fails.length, sizes, spacing, hues };
}

// Tab through the first controls; each focused control must show a visible focus style.
async function focusCheck(page) {
  const missing = [];
  let checked = 0;
  for (let i = 0; i < 12; i++) {
    await page.keyboard.press("Tab");
    const info = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return null;
      const st = getComputedStyle(el);
      const ring = (st.outlineStyle !== "none" && parseFloat(st.outlineWidth) > 0) || (st.boxShadow && st.boxShadow !== "none");
      return { ring, name: el.getAttribute("data-testid") || el.textContent.trim().slice(0, 30) || el.tagName.toLowerCase() };
    });
    if (!info) continue;
    checked++;
    if (!info.ring) missing.push(info.name);
  }
  return { checked, missing: Array.from(new Set(missing)).slice(0, 8) };
}


async function compareImagesInBrowser(browser, fileA, fileB, diffOutputPath, tolerance = 16) {
  if (!fs.existsSync(fileA) || !fs.existsSync(fileB)) return null;
  const dataA = "data:image/png;base64," + fs.readFileSync(fileA).toString("base64");
  const dataB = "data:image/png;base64," + fs.readFileSync(fileB).toString("base64");
  const context = await browser.newContext();
  const page = await context.newPage();
  try {
    await page.goto("about:blank");
    const result = await page.evaluate(async ({ dataA, dataB, tolerance }) => {
      const loadImg = (src) => new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = reject;
        img.src = src;
      });
      const [imgA, imgB] = await Promise.all([loadImg(dataA), loadImg(dataB)]);
      const w1 = imgA.naturalWidth, h1 = imgA.naturalHeight;
      const w2 = imgB.naturalWidth, h2 = imgB.naturalHeight;
      const MAX_PIXELS = 20000000;
      const MAX_DIM = 16384;
      if (w1 > MAX_DIM || h1 > MAX_DIM || (w1 * h1) > MAX_PIXELS ||
          w2 > MAX_DIM || h2 > MAX_DIM || (w2 * h2) > MAX_PIXELS) {
        return {
          error: `resource limit exceeded: image dimensions exceed maximum bound (${w1}x${h1} vs ${w2}x${h2})`,
          limitExceeded: true,
        };
      }
      if (w1 !== w2 || h1 !== h2) {
        return {
          differentDimensions: true,
          changedPercent: 100.0,
          w1, h1, w2, h2,
        };
      }
      const width = w1, height = h1;
      const cA = document.createElement("canvas");
      cA.width = width; cA.height = height;
      const ctxA = cA.getContext("2d");
      ctxA.drawImage(imgA, 0, 0);
      const imgDataA = ctxA.getImageData(0, 0, width, height).data;

      const cB = document.createElement("canvas");
      cB.width = width; cB.height = height;
      const ctxB = cB.getContext("2d");
      ctxB.drawImage(imgB, 0, 0);
      const imgDataB = ctxB.getImageData(0, 0, width, height).data;

      const diffCanvas = document.createElement("canvas");
      diffCanvas.width = width; diffCanvas.height = height;
      const diffCtx = diffCanvas.getContext("2d");
      const diffImgData = diffCtx.createImageData(width, height);
      const dData = diffImgData.data;

      let changedCount = 0;
      const blockSize = 20;
      const gridW = Math.ceil(width / blockSize);
      const gridH = Math.ceil(height / blockSize);
      const changedGrid = new Uint8Array(gridW * gridH);

      for (let y = 0; y < height; y++) {
        const gy = Math.floor(y / blockSize);
        for (let x = 0; x < width; x++) {
          const idx = (y * width + x) * 4;
          const dr = Math.abs(imgDataA[idx] - imgDataB[idx]);
          const dg = Math.abs(imgDataA[idx + 1] - imgDataB[idx + 1]);
          const db = Math.abs(imgDataA[idx + 2] - imgDataB[idx + 2]);
          const da = Math.abs(imgDataA[idx + 3] - imgDataB[idx + 3]);
          if (dr > tolerance || dg > tolerance || db > tolerance || da > tolerance) {
            changedCount++;
            changedGrid[gy * gridW + Math.floor(x / blockSize)] = 1;
            dData[idx] = 255;
            dData[idx + 1] = 0;
            dData[idx + 2] = 80;
            dData[idx + 3] = 255;
          } else {
            const gray = Math.round(0.299 * imgDataB[idx] + 0.587 * imgDataB[idx + 1] + 0.114 * imgDataB[idx + 2]);
            dData[idx] = gray;
            dData[idx + 1] = gray;
            dData[idx + 2] = gray;
            dData[idx + 3] = 100;
          }
        }
      }

      diffCtx.putImageData(diffImgData, 0, 0);
      const totalPixels = width * height;
      const changedPercent = totalPixels > 0 ? (changedCount / totalPixels) * 100 : 0;

      const regions = [];
      const visited = new Uint8Array(gridW * gridH);
      for (let gy = 0; gy < gridH; gy++) {
        for (let gx = 0; gx < gridW; gx++) {
          if (!changedGrid[gy * gridW + gx] || visited[gy * gridW + gx]) continue;
          let minX = gx, maxX = gx, minY = gy, maxY = gy;
          const q = [[gx, gy]];
          visited[gy * gridW + gx] = 1;
          while (q.length > 0) {
            const [curX, curY] = q.pop();
            minX = Math.min(minX, curX);
            maxX = Math.max(maxX, curX);
            minY = Math.min(minY, curY);
            maxY = Math.max(maxY, curY);
            for (let dy = -1; dy <= 1; dy++) {
              for (let dx = -1; dx <= 1; dx++) {
                const nx = curX + dx, ny = curY + dy;
                if (nx >= 0 && nx < gridW && ny >= 0 && ny < gridH) {
                  const nidx = ny * gridW + nx;
                  if (changedGrid[nidx] && !visited[nidx]) {
                    visited[nidx] = 1;
                    q.push([nx, ny]);
                  }
                }
              }
            }
          }
          const boxX = minX * blockSize;
          const boxY = minY * blockSize;
          const boxW = Math.min(width - boxX, (maxX - minX + 1) * blockSize);
          const boxH = Math.min(height - boxY, (maxY - minY + 1) * blockSize);
          regions.push([boxX, boxY, boxW, boxH]);
        }
      }

      let diffDataUrl = null;
      if (changedCount > 0) {
        diffDataUrl = diffCanvas.toDataURL("image/png");
      }
      return {
        differentDimensions: false,
        changedPercent: totalPixels > 0 ? (changedCount / totalPixels) * 100 : 0,
        changedPixels: changedCount,
        totalPixels,
        regions: regions.slice(0, 10),
        diffDataUrl,
      };
    }, { dataA, dataB, tolerance });

    if (result.diffDataUrl && diffOutputPath) {
      const base64Data = result.diffDataUrl.replace(/^data:image\/png;base64,/, "");
      fs.writeFileSync(diffOutputPath, Buffer.from(base64Data, "base64"));
      result.diffFile = path.basename(diffOutputPath);
    }
    delete result.diffDataUrl;
    return result;
  } finally {
    await context.close();
  }
}

async function audit(browser, run, shots) {
  const out = [];
  for (const viewport of ["desktop", "mobile"]) {
    const label = `${run.label}-${viewport}`;
    const lightShotPath = path.join(shots, `${run.label}-${viewport}.png`);
    const darkShotPath = path.join(shots, `${run.label}-${viewport}-dark.png`);
    const diffShotPath = path.join(shots, `${run.label}-${viewport}-diff.png`);

    // 1. Light render
    const lightResult = await withPage(browser, viewport, async (page, errors) => {
      await page.goto(run.url, { waitUntil: "load" });
      await page.screenshot({ path: lightShotPath, fullPage: true });
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
      const quality = await page.evaluate(measureQuality);
      quality.focus = await focusCheck(page);
      return { viewport, errors, ...facts, quality };
    }, shots, label, Boolean(run.video), { colorScheme: "light" });

    // 2. Dark render
    let darkQuality = null;
    let darkErrors = [];
    await withPage(browser, viewport, async (page, errors) => {
      await page.goto(run.url, { waitUntil: "load" });
      await page.screenshot({ path: darkShotPath, fullPage: true });
      darkQuality = await page.evaluate(measureQuality);
      darkQuality.focus = await focusCheck(page);
      darkErrors = errors || [];
    }, shots, `${label}-dark`, false, { colorScheme: "dark" });

    const darkDiff = await compareImagesInBrowser(browser, lightShotPath, darkShotPath, null, 16);
    let darkTheme = false;
    if (darkDiff && (darkDiff.differentDimensions || darkDiff.changedPixels > 0)) {
      darkTheme = true;
    }

    // 3. Drift against baseline if baseline exists
    let drift = null;
    if (run.baselines && run.baselines[viewport]) {
      drift = await compareImagesInBrowser(browser, run.baselines[viewport], lightShotPath, diffShotPath, 16);
    }

    out.push({
      ...lightResult,
      darkTheme,
      darkQuality,
      darkErrors,
      drift,
    });
  }
  return { label: run.label, viewports: out };
}

async function main() {
  const job = JSON.parse(fs.readFileSync(0, "utf8"));
  if (!pw) {
    console.log(JSON.stringify({ blocked: TRUSTED
      ? `Playwright is not installed in the trusted directory ${TRUSTED} (CGSPEC_PLAYWRIGHT_DIR)`
      : "Playwright is not installed for this project (npm i -D @playwright/test, then npx playwright install chromium)" }));
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
    for (const run of job.runs) {
      try {
        results.push(await (run.kind === "audit" ? audit : journey)(browser, run, job.shots));
      } catch (err) {
        results.push({ label: run.label, error: String(err && err.stack || err) });
      }
    }
  } finally {
    await browser.close();
  }
  console.log(JSON.stringify({ results }));
}

main().catch((e) => { console.log(JSON.stringify({ error: String(e && e.stack || e) })); process.exit(3); });
