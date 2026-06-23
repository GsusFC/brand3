"""Rendering helpers for Visual Signature platform shell."""

from __future__ import annotations

import html
import json
from typing import Any


def _render_index_html(payload: dict[str, Any]) -> str:
    embedded = html.escape(json.dumps(payload, ensure_ascii=False), quote=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Brand3 Platform</title>
  <link rel="stylesheet" href="./platform.css">
</head>
<body>
  <div id="app" class="page">
    <pre class="term-head"><span class="prompt">❯</span> brand3-platform <span class="hl-accent">--mode</span> local <span class="dim">· read-only · separated layers</span></pre>
    <hr class="rule">
    <section class="static-skeleton">
      <h1 class="page-title">Brand3 Platform</h1>
      <p class="intro-copy">Loading local Brand3 scoring and Visual Signature artifacts. This static shell stays readable if JavaScript fails.</p>
      <div class="guardrail-banner">Read-only local navigation surface. No scoring changes, rubric changes, production UI changes, provider calls, or runtime mutation enablement.</div>
    </section>
    <script id="platform-data" type="application/json">{embedded}</script>
  </div>
  <script src="./platform.js" defer></script>
</body>
</html>
"""


def _platform_css() -> str:
    return """
@import url("https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap");

:root {
  color-scheme: light;
  --bg: #eeeeee;
  --surface: #f5f5f5;
  --surface-2: #eeeeee;
  --surface-3: #e9e9e9;
  --border: #e4e4e4;
  --text: #161616;
  --muted: #77736d;
  --soft: #9a958e;
  --accent: #ef490d;
  --success: #5f745c;
  --warning: #b7792b;
  --danger: #b84f3f;
  --font-mono: "JetBrains Mono", monospace;
}

* { box-sizing: border-box; }
html, body { min-height: 100%; }
body {
  margin: 0;
  padding: 0;
  background:
    repeating-linear-gradient(135deg, rgba(22, 22, 22, 0.018) 0 1px, transparent 1px 7px),
    var(--bg);
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  text-rendering: geometricPrecision;
  font-feature-settings: "liga" 0, "calt" 0;
}
a { color: inherit; text-decoration: underline; text-decoration-color: rgba(239, 73, 13, 0.58); text-underline-offset: 3px; }
a:hover { color: var(--accent); }
button, input, select, textarea { font: inherit; }
.page {
  width: min(1440px, calc(100% - 48px));
  min-height: calc(100vh - 48px);
  margin: 24px auto;
  background: rgba(245, 245, 245, 0.94);
  border: 1px solid var(--border);
  box-shadow: 0 10px 32px rgba(22, 22, 22, 0.035);
}
.term-head {
  min-height: 44px;
  display: flex;
  align-items: center;
  margin: 0;
  padding: 0 28px;
  border-bottom: 1px solid var(--border);
  background: rgba(238, 238, 238, 0.76);
  font-size: 12px;
  white-space: pre-wrap;
}
.prompt, .hl-accent { color: var(--accent); font-weight: 700; }
.dim, .small { color: var(--muted); }
.rule { border: 0; border-top: 1px solid var(--border); margin: 0; }
.rule-thin { border: 0; border-top: 1px dashed var(--border); margin: 24px 0; }
section { padding: 28px; }
.page-title { max-width: 860px; margin: 0 0 16px; font-size: 26px; line-height: 1.18; }
.intro-copy { margin: 0 0 20px; color: var(--muted); }
.platform-shell {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 0;
}
.left-nav {
  border-right: 1px solid var(--border);
  background: rgba(238, 238, 238, 0.42);
  padding: 20px;
  position: sticky;
  top: 0;
  min-height: calc(100vh - 94px);
}
.nav-title { margin: 0 0 14px; font-size: 12px; text-transform: uppercase; }
.nav-button {
  width: 100%;
  display: block;
  text-align: left;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  padding: 9px 10px;
  margin: 0 0 8px;
  cursor: pointer;
}
.nav-button.active { border-color: var(--accent); color: var(--accent); }
.main-content { min-width: 0; }
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 18px;
  margin: 0 0 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}
.section-head .label { font-size: 12px; font-weight: 700; text-transform: uppercase; }
.section-head .tag { color: var(--soft); font-size: 12px; text-align: right; }
.guardrail-banner {
  border: 1px dashed var(--accent);
  background: rgba(242, 222, 212, 0.42);
  color: var(--text);
  padding: 12px;
}
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.card {
  border: 1px solid var(--border);
  background: var(--surface);
  padding: 16px;
}
.card h3, .card h4 { margin: 0 0 10px; font-size: 13px; }
.badge-line, .artifact-list, .screenshot-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.badge {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  padding: 4px 8px;
  font-size: 12px;
}
.badge.ok { color: var(--success); border-color: rgba(95, 116, 92, 0.4); }
.badge.warn { color: var(--warning); border-color: rgba(183, 121, 43, 0.4); }
.badge.bad { color: var(--danger); border-color: rgba(184, 79, 63, 0.4); }
.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
}
.metric {
  border: 1px solid var(--border);
  background: rgba(238, 238, 238, 0.56);
  padding: 10px;
  min-width: 0;
}
.metric .k { color: var(--muted); font-size: 12px; margin-bottom: 4px; }
.metric .v { overflow-wrap: anywhere; }
.items {
  display: grid;
  gap: 12px;
  margin-top: 14px;
}
.item-card {
  border: 1px solid var(--border);
  background: rgba(245, 245, 245, 0.65);
  padding: 12px;
}
.item-title { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 8px; font-weight: 700; }
.screenshot-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}
.screenshot-tile {
  border: 1px solid var(--border);
  background: #fff;
  text-decoration: none;
  color: inherit;
}
.screenshot-tile img {
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
  display: block;
  border-bottom: 1px solid var(--border);
}
.screenshot-tile span { display: block; padding: 6px 8px; font-size: 12px; color: var(--muted); }
details {
  border: 1px solid var(--border);
  background: var(--surface);
  padding: 12px;
  margin-top: 14px;
}
summary { cursor: pointer; font-weight: 700; }
pre.raw-json {
  white-space: pre-wrap;
  overflow: auto;
  max-height: 360px;
  background: #fafafa;
  border: 1px solid var(--border);
  padding: 12px;
}
.footer {
  margin-top: 0;
  padding: 18px 28px 24px;
  border-top: 1px solid var(--border);
  background: rgba(238, 238, 238, 0.7);
  color: var(--muted);
  font-size: 12px;
}
.kv { display: grid; grid-template-columns: 160px 1fr; row-gap: 4px; column-gap: 14px; }
.kv .k { color: var(--accent); }
.kv .v { color: var(--text); }
.footer-note, .footer-cursor { margin-top: 12px; }
.cursor { display: inline-block; width: 7px; height: 14px; background: var(--accent); vertical-align: -2px; animation: blink 1.05s steps(1, end) infinite; margin-left: 4px; }
@keyframes blink { 0%, 55% { opacity: 1; } 56%, 100% { opacity: 0; } }
@media (max-width: 1100px) {
  .platform-shell { grid-template-columns: 1fr; }
  .left-nav { position: static; min-height: 0; border-right: 0; border-bottom: 1px solid var(--border); }
  .dashboard-grid, .screenshot-grid { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 720px) {
  .page { width: min(100% - 32px, 760px); margin-top: 16px; }
  section { padding: 18px; }
  .dashboard-grid, .metric-grid, .screenshot-grid { grid-template-columns: 1fr; }
}
""".strip()


def _platform_js() -> str:
    return """
(function () {
  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function badgeClass(value) {
    const text = String(value || "").toLowerCase();
    if (["ready", "valid", "ok", "confirmed", "reviewed", "governed"].some((token) => text.includes(token))) return "ok";
    if (["missing", "error", "failed"].some((token) => text.includes(token))) return "bad";
    return "warn";
  }

  function renderValue(value) {
    if (value === null || value === undefined || value === "") return "n/a";
    if (Array.isArray(value)) {
      if (!value.length) return "none";
      if (value.every((item) => item === null || ["string", "number", "boolean"].includes(typeof item))) {
        return value.map(escapeHtml).join("<br>");
      }
      return `<pre class="raw-json">${escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
    }
    if (typeof value === "object") return `<pre class="raw-json">${escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
    if (typeof value === "string" && isLocalArtifactPath(value)) {
      return `<a href="${escapeHtml(value)}" target="_blank" rel="noreferrer">${escapeHtml(value)}</a>`;
    }
    return escapeHtml(value);
  }

  function isLocalArtifactPath(value) {
    return /^(\\.\\.\\/|\\.\\/|[\\w.-]+\\/).+\\.(json|html|md|png|jpg|jpeg|sqlite3|db)$/i.test(value);
  }

  const dataNode = document.getElementById("platform-data");
  const app = document.getElementById("app");

  try {
    if (!dataNode || !app) throw new Error("platform data or root missing");
    const data = JSON.parse(dataNode.textContent || "{}");
    const sections = asArray(data.sections);
    let activeKey = sections[0] && sections[0].key || "brand3-overview";
    const artifactMap = Object.fromEntries(asArray(data.artifacts).map((artifact) => [artifact.key, artifact]));

    function render() {
      const active = sections.find((section) => section.key === activeKey) || sections[0];
      app.innerHTML = `
        <pre class="term-head"><span class="prompt">❯</span> brand3-platform <span class="hl-accent">--status</span> ${escapeHtml(data.platform_status)} <span class="dim">· read-only · separated layers</span></pre>
        <hr class="rule">
        <div class="platform-shell">
          <nav class="left-nav">
            <h2 class="nav-title">Brand3 Platform</h2>
            ${asArray(data.navigation).map((item) => `<button class="nav-button ${item.key === active.key ? "active" : ""}" data-section="${escapeHtml(item.key)}">${escapeHtml(item.label)}</button>`).join("")}
            <div class="guardrail-banner small">No provider calls · no scoring changes · no rubric changes · no runtime mutation enablement.</div>
          </nav>
          <main class="main-content">${renderSection(active)}</main>
        </div>
        <hr class="rule">
        <footer class="footer">
          <div class="kv">
            <span class="k">engine</span>    <span class="v">brand3 local platform</span>
            <span class="k">about</span>     <span class="v">read-only dashboard · separated layers · JSON source of truth · Markdown audit/export</span>
          </div>
          <div class="small footer-note">${escapeHtml(asArray(data.notes)[0] || "Static local dashboard.")}</div>
          <div class="footer-cursor"><span class="prompt">❯</span> _<span class="cursor"></span></div>
        </footer>
      `;
      app.querySelectorAll("[data-section]").forEach((button) => {
        button.addEventListener("click", () => {
          activeKey = button.getAttribute("data-section");
          render();
        });
      });
    }

    function renderSection(section) {
      return `
        <section id="${escapeHtml(section.key)}">
          <div class="section-head">
            <span class="label">${escapeHtml(section.title)}</span>
            <span class="tag">// ${escapeHtml(section.status)}</span>
          </div>
          <h1 class="page-title">${escapeHtml(section.title)}</h1>
          <p class="intro-copy">${escapeHtml(section.summary)}</p>
          <div class="badge-line">
            <span class="badge ${badgeClass(section.status)}">${escapeHtml(section.status)}</span>
            ${asArray(section.badges).map((badge) => `<span class="badge">${escapeHtml(badge)}</span>`).join("")}
          </div>
          ${section.key === "brand3-overview" ? renderGuardrails() : ""}
          ${renderMetrics(section.metrics)}
          ${renderItems(section)}
          ${renderArtifacts(section.artifact_keys)}
          ${renderNextSteps(section)}
          <details>
            <summary>Advanced / debug</summary>
            <pre class="raw-json">${escapeHtml(JSON.stringify(section, null, 2))}</pre>
          </details>
        </section>
      `;
    }

    function renderGuardrails() {
      return `
        <div class="dashboard-grid" style="margin-top:14px;">
          ${asArray(data.guardrails).map((guardrail) => `<div class="card"><h3>${escapeHtml(guardrail)}</h3><div class="small">enforced as local platform scope</div></div>`).join("")}
        </div>
      `;
    }

    function renderMetrics(metrics) {
      const entries = Object.entries(metrics || {});
      if (!entries.length) return "";
      return `<div class="metric-grid">${entries.map(([key, value]) => `<div class="metric"><div class="k">${escapeHtml(key)}</div><div class="v">${renderValue(value)}</div></div>`).join("")}</div>`;
    }

    function renderItems(section) {
      const items = asArray(section.items);
      if (!items.length) return "";
      return `<div class="items">${items.map((item) => renderItem(section.key, item)).join("")}</div>`;
    }

    function renderItem(sectionKey, item) {
      const title = item.brand_name || item.capability_id || item.queue_id || item.capture_id || "item";
      const status = item.queue_state || item.perceptual_state || item.agreement || item.maturity_state || item.review_outcome || "record";
      return `
        <div class="item-card">
          <div class="item-title"><span>${escapeHtml(title)}</span><span class="badge ${badgeClass(status)}">${escapeHtml(status)}</span></div>
          <div class="metric-grid">${Object.entries(item).filter(([key]) => !["screenshots"].includes(key)).slice(0, 8).map(([key, value]) => `<div class="metric"><div class="k">${escapeHtml(key)}</div><div class="v">${renderValue(value)}</div></div>`).join("")}</div>
          ${sectionKey === "captures" ? renderScreenshots(item.screenshots) : ""}
        </div>
      `;
    }

    function renderScreenshots(screenshots) {
      const rows = asArray(screenshots);
      if (!rows.length) return "";
      return `<div class="screenshot-grid">${rows.map((shot) => `<a class="screenshot-tile" href="${escapeHtml(shot.path)}" target="_blank" rel="noreferrer"><img src="${escapeHtml(shot.path)}" alt="${escapeHtml(shot.label)} screenshot"><span>${escapeHtml(shot.label)}</span></a>`).join("")}</div>`;
    }

    function renderArtifacts(keys) {
      const artifacts = asArray(keys).map((key) => artifactMap[key]).filter(Boolean);
      if (!artifacts.length) return "";
      return `
        <details>
          <summary>Source artifacts</summary>
          <div class="artifact-list" style="margin-top:12px;">
            ${artifacts.map((artifact) => `<a class="badge ${artifact.exists ? "ok" : "bad"}" href="${escapeHtml(artifact.path)}" target="_blank" rel="noreferrer">${escapeHtml(artifact.label)}</a>`).join("")}
          </div>
        </details>
      `;
    }

    function renderNextSteps(section) {
      const steps = [...asArray(section.next_steps)];
      if (section.key === "brand3-overview") steps.push(...asArray(data.next_steps));
      if (!steps.length) return "";
      return `<div class="card" style="margin-top:14px;"><h3>What to do next</h3>${steps.map((step) => `<div class="small">- ${escapeHtml(step)}</div>`).join("")}</div>`;
    }

    render();
  } catch (error) {
    if (app) {
      app.innerHTML = `<section><h1>Brand3 Platform failed to load</h1><pre class="raw-json">${escapeHtml(error && error.stack ? error.stack : String(error))}</pre></section>`;
    }
    if (typeof console !== "undefined" && console.error) console.error(error);
  }
})();
""".strip()
