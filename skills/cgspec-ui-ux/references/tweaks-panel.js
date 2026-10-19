/* CGSpec tweaks panel: lets the user change type, density, accent, radius and light/dark on a live
   prototype instead of describing changes in words. No dependencies. Include it with
     <script src="tweaks-panel.js" defer></script>
   and style the page with these CSS custom properties (the token roles of the register):
     --font-sans, --text-base (px), --type-ratio, --space-unit (px), --accent, --radius (px), [data-theme="dark"]
   Toggle with the "Tweaks" button or the T key; "Copy values" gives JSON to paste back to the agent, which
   records the choice in the register or token sheet. Remove the script from the real frontend after layer 6. */
(function () {
  "use strict";
  if (window.__cgspecTweaks) return;
  window.__cgspecTweaks = true;
  var root = document.documentElement;
  var css = getComputedStyle(root);
  var read = function (name, fallback) { return (css.getPropertyValue(name) || "").trim() || fallback; };
  var state = {
    "--font-sans": read("--font-sans", "system-ui, sans-serif"),
    "--text-base": parseFloat(read("--text-base", "15")),
    "--type-ratio": parseFloat(read("--type-ratio", "1.2")),
    "--space-unit": parseFloat(read("--space-unit", "8")),
    "--accent": read("--accent", "#2f6f5e"),
    "--radius": parseFloat(read("--radius", "6")),
    theme: root.getAttribute("data-theme") || "light"
  };
  var fonts = ["system-ui, sans-serif", "'Inter', system-ui, sans-serif", "'IBM Plex Sans', system-ui, sans-serif",
               "'Source Serif 4', Georgia, serif", "ui-monospace, monospace"];
  if (fonts.indexOf(state["--font-sans"]) < 0) fonts.unshift(state["--font-sans"]);
  function apply() {
    root.style.setProperty("--font-sans", state["--font-sans"]);
    ["--text-base", "--space-unit", "--radius"].forEach(function (k) { root.style.setProperty(k, state[k] + "px"); });
    root.style.setProperty("--type-ratio", String(state["--type-ratio"]));
    root.style.setProperty("--accent", state["--accent"]);
    root.setAttribute("data-theme", state.theme);
  }
  var panel = document.createElement("div");
  panel.setAttribute("data-cgspec-tweaks", "");
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-label", "Design tweaks");
  panel.style.cssText = "position:fixed;right:12px;bottom:56px;z-index:2147483647;width:250px;padding:12px;" +
    "background:#fff;color:#111;border:1px solid #ccc;border-radius:8px;font:13px/1.4 system-ui,sans-serif;" +
    "box-shadow:0 4px 16px rgba(0,0,0,.15);display:none";
  function row(label, input) {
    var wrap = document.createElement("label");
    wrap.style.cssText = "display:block;margin:0 0 8px";
    wrap.textContent = label;
    input.style.cssText = "display:block;width:100%;margin-top:2px";
    wrap.appendChild(input);
    panel.appendChild(wrap);
    return input;
  }
  function range(key, min, max, step, label) {
    var input = document.createElement("input");
    input.type = "range"; input.min = min; input.max = max; input.step = step; input.value = state[key];
    input.setAttribute("data-testid", "tweaks-" + key.replace(/^--/, ""));
    row(label, input).addEventListener("input", function () { state[key] = parseFloat(input.value); apply(); });
  }
  var font = document.createElement("select");
  font.setAttribute("data-testid", "tweaks-font");
  fonts.forEach(function (f) { var o = document.createElement("option"); o.value = f; o.textContent = f.split(",")[0].replace(/'/g, ""); font.appendChild(o); });
  font.value = state["--font-sans"];
  row("Typeface", font).addEventListener("change", function () { state["--font-sans"] = font.value; apply(); });
  range("--text-base", 12, 20, 0.5, "Base text size");
  range("--type-ratio", 1.1, 1.5, 0.025, "Type scale ratio");
  range("--space-unit", 2, 12, 1, "Density (spacing unit)");
  range("--radius", 0, 16, 1, "Corner radius");
  var accent = document.createElement("input");
  accent.type = "color"; accent.value = /^#[0-9a-f]{6}$/i.test(state["--accent"]) ? state["--accent"] : "#2f6f5e";
  accent.setAttribute("data-testid", "tweaks-accent");
  row("Accent", accent).addEventListener("input", function () { state["--accent"] = accent.value; apply(); });
  var theme = document.createElement("select");
  theme.setAttribute("data-testid", "tweaks-theme");
  ["light", "dark"].forEach(function (t) { var o = document.createElement("option"); o.value = t; o.textContent = t; theme.appendChild(o); });
  theme.value = state.theme;
  row("Light or dark", theme).addEventListener("change", function () { state.theme = theme.value; apply(); });
  var copy = document.createElement("button");
  copy.type = "button"; copy.textContent = "Copy values";
  copy.setAttribute("data-testid", "tweaks-copy");
  copy.style.cssText = "width:100%;padding:6px;margin-top:4px;cursor:pointer";
  copy.addEventListener("click", function () {
    var text = JSON.stringify(state, null, 2);
    (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject()).then(
      function () { copy.textContent = "Copied: paste it to the agent"; },
      function () { window.prompt("Copy these values and paste them to the agent:", text); });
  });
  panel.appendChild(copy);
  var toggle = document.createElement("button");
  toggle.type = "button"; toggle.textContent = "Tweaks";
  toggle.setAttribute("data-testid", "tweaks-toggle");
  toggle.setAttribute("aria-expanded", "false");
  toggle.style.cssText = "position:fixed;right:12px;bottom:12px;z-index:2147483647;padding:8px 12px;min-height:36px;" +
    "border-radius:18px;border:1px solid #999;background:#111;color:#fff;font:13px system-ui,sans-serif;cursor:pointer";
  function show(open) { panel.style.display = open ? "block" : "none"; toggle.setAttribute("aria-expanded", String(open)); }
  toggle.addEventListener("click", function () { show(panel.style.display === "none"); });
  document.addEventListener("keydown", function (e) {
    var tag = (e.target && e.target.tagName) || "";
    if ((e.key === "t" || e.key === "T") && !/INPUT|TEXTAREA|SELECT/.test(tag) && !e.metaKey && !e.ctrlKey) {
      show(panel.style.display === "none");
    }
  });
  function mount() { document.body.appendChild(panel); document.body.appendChild(toggle); apply(); }
  if (document.body) mount(); else document.addEventListener("DOMContentLoaded", mount);
})();
