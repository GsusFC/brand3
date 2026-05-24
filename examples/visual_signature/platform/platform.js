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
    return /^(\.\.\/|\.\/|[\w.-]+\/).+\.(json|html|md|png|jpg|jpeg|sqlite3|db)$/i.test(value);
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