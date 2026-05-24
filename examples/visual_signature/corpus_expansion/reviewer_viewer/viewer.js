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

  function countBy(items, getKey) {
    const counts = {};
    asArray(items).forEach((item) => {
      const key = getKey(item) || "unknown";
      counts[key] = (counts[key] || 0) + 1;
    });
    return counts;
  }

  function summarizeTargets(targets) {
    const list = asArray(targets);
    const ownerDistribution = countBy(list, (target) => target.affordance_owner);
    const policyDistribution = countBy(list, (target) => target.interaction_policy);
    const safe = list.filter((target) => target.interaction_policy === "safe_to_dismiss");
    const unsafe = list.filter((target) => target.interaction_policy === "unsafe_to_mutate");
    const reviewOnly = list.filter((target) => target.interaction_policy === "requires_human_review");
    return {
      ownerDistribution,
      policyDistribution,
      safeHighlights: safe.slice(0, 3).map((target) => `${target.label || "target"} · ${target.affordance_category || "unknown"} · ${target.affordance_owner || "unknown_owner"}`),
      unsafeHighlights: unsafe.slice(0, 3).map((target) => `${target.label || "target"} · ${target.affordance_category || "unknown"} · ${target.affordance_owner || "unknown_owner"}`),
      reviewOnlyHighlights: reviewOnly.slice(0, 3).map((target) => `${target.label || "target"} · ${target.affordance_category || "unknown"} · ${target.affordance_owner || "unknown_owner"}`),
      total: list.length,
    };
  }

  function screenshotLabel(src, index) {
    const name = String(src).split("/").pop() || `screenshot-${index + 1}`;
    if (name.includes("clean-attempt")) {
      return "Clean attempt";
    }
    if (name.includes("full-page")) {
      return "Full page";
    }
    if (index === 0) {
      return "Raw viewport";
    }
    return name.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " ");
  }

  function preferredScreenshotIndex(screenshots) {
    const fullPageIndex = asArray(screenshots).findIndex((src) => String(src).includes("full-page"));
    return fullPageIndex >= 0 ? fullPageIndex : 0;
  }

  const dataNode = document.getElementById("viewer-data");
  const app = document.getElementById("app");

  function renderError(error) {
    if (!app) {
      return;
    }
    app.innerHTML = `
      <div class="viewer-error">
        <div class="viewer-error-card">
          <h1>Visual Signature Reviewer Viewer failed to load</h1>
          <div class="muted">The bundle hit a local parsing or rendering error. The page stays evidence-only and offline.</div>
          <pre>${escapeHtml(error && error.stack ? error.stack : String(error))}</pre>
        </div>
      </div>
    `;
  }

  try {
    if (!dataNode) throw new Error("viewer data node missing");
    if (!app) throw new Error("root container missing");

    const data = JSON.parse(dataNode.textContent || "{}");
    if (!Array.isArray(data.packets) || data.packets.length === 0) {
      throw new Error("no reviewer packets available");
    }

    const state = {
      activeQueueId: data.selected_review_queue_item_ids[0] || data.packets[0].queue_id,
      activeScreenshotIndex: preferredScreenshotIndex(data.packets[0] && data.packets[0].screenshot_paths),
      drafts: {},
    };

    app.innerHTML = `
      <pre class="term-head"><span class="prompt">❯</span> visual-signature-reviewer <span class="hl-accent">--scope</span> ${escapeHtml(data.readiness_scope)} <span class="hl-accent">--pilot</span> ${escapeHtml(data.pilot_status)} <span class="dim">· ${data.packet_count} packets · offline evidence-only</span></pre>
      <hr class="rule">
      <section class="viewer-workspace">
      <main class="main">
        <div class="queue-strip">
          <div class="small">Review queue</div>
          <div id="queueList" class="queue-list"></div>
        </div>
        <header class="hero">
          <div>
            <div class="eyebrow">Active packet</div>
            <h2 id="packetTitle"></h2>
            <div id="packetSubtitle" class="subtle"></div>
          </div>
          <div id="heroBadges" class="badge-line"></div>
        </header>

        <section class="card screenshot-card">
          <div class="card-head">
            <div>
              <h3>Screenshot viewer</h3>
              <p>Raw viewport first. Clean attempt is shown only when available.</p>
            </div>
          </div>
          <div id="screenshotTabs" class="screenshot-tabs"></div>
          <div id="screenshotStage" class="screenshot-stage"></div>
        </section>

        <section class="card review-question">
          <div class="card-head">
            <div>
              <h3>Review question</h3>
              <p>Make one evidence-grounded call. Leave the item unresolved if the evidence is not enough.</p>
            </div>
          </div>
          <div id="reviewQuestion" class="question"></div>
          <div id="outcomeChips" class="question-meta badge-line"></div>
        </section>

        <section id="summaryGrid" class="summary-grid"></section>

        <details class="details-panel">
          <summary>Advanced evidence</summary>
          <div class="details-body">
            <div class="two-col">
              <div class="compact-block">
                <h4>Affordance highlights</h4>
                <div id="affordanceHighlights" class="summary-list"></div>
              </div>
              <div class="compact-block">
                <h4>Owner distribution</h4>
                <div id="ownerDistribution" class="summary-list compact"></div>
              </div>
            </div>
            <div class="compact-block">
              <h4>Raw evidence refs</h4>
              <div id="rawEvidenceRefs" class="summary-list"></div>
            </div>
            <div class="compact-block">
              <h4>Packet source</h4>
              <div class="muted">Source markdown remains external to avoid repeating the same evidence in this view.</div>
              <div id="packetSourceLink" class="summary-list"></div>
            </div>
          </div>
        </details>

        <details class="details-panel">
          <summary>Raw JSON</summary>
          <div class="details-body">
            <div class="two-col">
              <div class="compact-block">
                <h4>Capture manifest excerpt</h4>
                <pre id="captureManifestJson" class="raw-json"></pre>
              </div>
              <div class="compact-block">
                <h4>Dismissal audit excerpt</h4>
                <pre id="dismissalAuditJson" class="raw-json"></pre>
              </div>
            </div>
          </div>
        </details>

        <details class="details-panel">
          <summary>Debug diagnostics</summary>
          <div class="details-body">
            <pre id="debugDiagnostics" class="raw-json"></pre>
          </div>
        </details>
      </main>

      <aside class="right-panel">
        <div class="card">
          <h3>Decision form</h3>
          <form id="decisionForm" class="decision-form">
            <div class="form-row">
              <label for="reviewerId">Reviewer ID</label>
              <input id="reviewerId" name="reviewer_id" type="text" placeholder="reviewer-01">
            </div>
            <div class="form-row">
              <label for="reviewOutcome">Outcome</label>
              <select id="reviewOutcome" name="review_outcome"></select>
            </div>
            <div class="form-row">
              <label for="confidenceBucket">Confidence</label>
              <select id="confidenceBucket" name="confidence_bucket">
                <option value="unknown">unknown</option>
                <option value="low">low</option>
                <option value="medium">medium</option>
                <option value="high">high</option>
              </select>
            </div>
            <div class="form-row">
              <label for="reviewNotes">Notes</label>
              <textarea id="reviewNotes" name="notes" placeholder="Evidence-based note..."></textarea>
            </div>
            <div class="form-row">
              <label for="evidenceNotes">Evidence notes</label>
              <textarea id="evidenceNotes" name="evidence_notes" placeholder="What evidence supports this decision?"></textarea>
            </div>
            <div class="form-row">
              <label for="contradictionNotes">Contradiction notes</label>
              <textarea id="contradictionNotes" name="contradiction_notes" placeholder="What does not match the current interpretation?"></textarea>
            </div>
            <div class="form-row">
              <label for="additionalEvidence">Additional evidence needed</label>
              <textarea id="additionalEvidence" name="additional_evidence_needed" placeholder="What else would resolve uncertainty?"></textarea>
            </div>
            <div class="button-row">
              <button class="button primary" type="submit">Store local draft</button>
              <button class="button" type="button" id="clearDraft">Clear local draft</button>
            </div>
          </form>
        </div>

        <div class="card">
          <h3>Form guidance</h3>
          <div class="small">Required fields</div>
          <div id="requiredFields" class="summary-list"></div>
          <hr class="summary-divider">
          <div class="small">Unresolved handling</div>
          <div id="unresolvedGuidance" class="summary-list"></div>
          <hr class="summary-divider">
          <div class="small">Contradiction handling</div>
          <div id="contradictionGuidance" class="summary-list"></div>
        </div>

        <div class="draft-banner" id="draftBanner">No local draft stored.</div>
      </aside>
      </section>
      <hr class="rule">
      <footer class="footer">
        <div class="kv">
          <span class="k">engine</span>    <span class="v">brand3 visual signature</span>
          <span class="k">about</span>     <span class="v">local-only reviewer · no persistence · evidence-only</span>
        </div>
        <div class="small footer-note">Reviewer drafts stay in memory and are not written to disk.</div>
        <div class="footer-cursor"><span class="prompt">❯</span> _<span class="cursor"></span></div>
      </footer>
    `;

    const queueList = document.getElementById("queueList");
    const packetTitle = document.getElementById("packetTitle");
    const packetSubtitle = document.getElementById("packetSubtitle");
    const heroBadges = document.getElementById("heroBadges");
    const screenshotTabs = document.getElementById("screenshotTabs");
    const screenshotStage = document.getElementById("screenshotStage");
    const reviewQuestion = document.getElementById("reviewQuestion");
    const outcomeChips = document.getElementById("outcomeChips");
    const summaryGrid = document.getElementById("summaryGrid");
    const affordanceHighlights = document.getElementById("affordanceHighlights");
    const ownerDistribution = document.getElementById("ownerDistribution");
    const rawEvidenceRefs = document.getElementById("rawEvidenceRefs");
    const packetSourceLink = document.getElementById("packetSourceLink");
    const captureManifestJson = document.getElementById("captureManifestJson");
    const dismissalAuditJson = document.getElementById("dismissalAuditJson");
    const debugDiagnostics = document.getElementById("debugDiagnostics");
    const requiredFields = document.getElementById("requiredFields");
    const unresolvedGuidance = document.getElementById("unresolvedGuidance");
    const contradictionGuidance = document.getElementById("contradictionGuidance");
    const reviewOutcome = document.getElementById("reviewOutcome");
    const reviewerId = document.getElementById("reviewerId");
    const confidenceBucket = document.getElementById("confidenceBucket");
    const reviewNotes = document.getElementById("reviewNotes");
    const evidenceNotes = document.getElementById("evidenceNotes");
    const contradictionNotes = document.getElementById("contradictionNotes");
    const additionalEvidence = document.getElementById("additionalEvidence");
    const draftBanner = document.getElementById("draftBanner");
    const decisionForm = document.getElementById("decisionForm");
    const clearDraft = document.getElementById("clearDraft");

    const initialPacket = data.packets[0];
    reviewOutcome.innerHTML = asArray(initialPacket.allowed_outcomes).map((outcome) => `<option value="${escapeHtml(outcome)}">${escapeHtml(outcome)}</option>`).join("");

    function currentPacket() {
      return data.packets.find((packet) => packet.queue_id === state.activeQueueId) || initialPacket;
    }

    function currentTargetSummary(packet) {
      return summarizeTargets([
        ...asArray(packet.capture_manifest_entry && packet.capture_manifest_entry.candidate_click_targets),
        ...asArray(packet.capture_manifest_entry && packet.capture_manifest_entry.rejected_click_targets),
      ]);
    }

    function renderQueue() {
      queueList.innerHTML = "";
      data.packets.forEach((packet) => {
        const button = document.createElement("button");
        button.className = "queue-item" + (packet.queue_id === state.activeQueueId ? " active" : "");
        button.innerHTML = `
          <div class="title">
            <span>${escapeHtml(packet.brand_name)}</span>
          </div>
        `;
        button.addEventListener("click", () => {
            state.activeQueueId = packet.queue_id;
            state.activeScreenshotIndex = preferredScreenshotIndex(packet.screenshot_paths);
            render();
          });
        queueList.appendChild(button);
      });
    }

    function renderScreenshots(packet) {
      const screenshots = asArray(packet.screenshot_paths);
      screenshotTabs.innerHTML = "";
      if (screenshots.length === 0) {
        screenshotTabs.innerHTML = `<div class="small">No screenshot paths available.</div>`;
      } else {
        screenshots.forEach((src, index) => {
          const tab = document.createElement("button");
          tab.className = "tab-button" + (index === state.activeScreenshotIndex ? " active" : "");
          tab.textContent = screenshotLabel(src, index);
          tab.addEventListener("click", () => {
            state.activeScreenshotIndex = index;
            renderScreenshots(packet);
          });
          screenshotTabs.appendChild(tab);
        });
      }

      const activeSrc = screenshots[state.activeScreenshotIndex] || screenshots[0] || "";
      screenshotStage.className = "screenshot-stage" + (String(activeSrc).includes("full-page") ? " full-page" : "");
      screenshotStage.innerHTML = `
        <div class="screenshot-fallback" ${activeSrc ? "hidden" : ""}>
          <strong>Screenshot unavailable.</strong>
          <div>${escapeHtml(packet.brand_name)} has no visible screenshot path for this view.</div>
        </div>
        ${activeSrc ? `<img src="${escapeHtml(activeSrc)}" alt="${escapeHtml(packet.brand_name)} ${escapeHtml(screenshotLabel(activeSrc, state.activeScreenshotIndex))}">` : ""}
      `;
      const img = screenshotStage.querySelector("img");
      const fallback = screenshotStage.querySelector(".screenshot-fallback");
      if (img && fallback) {
        img.addEventListener("load", () => { fallback.hidden = true; });
        img.addEventListener("error", () => { fallback.hidden = false; });
      }

    }

    function renderEvidenceSummaries(packet) {
      const targetSummary = currentTargetSummary(packet);
      const captureEntry = packet.capture_manifest_entry || {};
      const dismissalEntry = packet.dismissal_audit_entry || {};
      const safeHighlights = targetSummary.safeHighlights.length > 0 ? targetSummary.safeHighlights : ["No safe-to-dismiss highlight."];
      const unsafeHighlights = targetSummary.unsafeHighlights.length > 0 ? targetSummary.unsafeHighlights : ["No unsafe-to-mutate highlight."];
      const reviewOnlyHighlights = targetSummary.reviewOnlyHighlights.length > 0 ? targetSummary.reviewOnlyHighlights : ["No review-only highlight."];
      const ownerChips = Object.entries(dismissalEntry.affordance_owner_distribution || targetSummary.ownerDistribution)
        .map(([key, value]) => `<span class="badge neutral">${escapeHtml(key)} · ${value}</span>`)
        .join("");
      const policyChips = Object.entries(targetSummary.policyDistribution)
        .map(([key, value]) => `<span class="badge neutral">${escapeHtml(key)} · ${value}</span>`)
        .join("");

      summaryGrid.innerHTML = `
        <div class="summary-card">
          <div class="summary-label">Obstruction</div>
          <div class="summary-value">${escapeHtml(packet.obstruction_summary || "No obstruction summary available.")}</div>
          <div class="summary-list" style="margin-top:10px;">
            <span class="badge ${packet.perceptual_state_summary && packet.perceptual_state_summary.includes("UNSAFE_MUTATION_BLOCKED") ? "bad" : "warn"}">${escapeHtml(String(captureEntry.dismissal_eligibility || packet.queue_state || "unknown"))}</span>
            <span class="badge neutral">${escapeHtml(String(captureEntry.dismissal_attempted ? "attempted" : "not attempted"))}</span>
          </div>
        </div>
        <div class="summary-card">
          <div class="summary-label">Affordance</div>
          <div class="summary-value">
            <strong>Safe:</strong> ${escapeHtml(safeHighlights.join(" · "))}
            <br>
            <strong>Unsafe:</strong> ${escapeHtml(unsafeHighlights.join(" · "))}
            <br>
            <strong>Review-only:</strong> ${escapeHtml(reviewOnlyHighlights.join(" · "))}
          </div>
          <div class="summary-list" style="margin-top:10px;">${policyChips}</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">Perceptual state</div>
          <div class="summary-value">${escapeHtml(packet.perceptual_state_summary || "No state summary available.")}</div>
          <div class="summary-list compact" style="margin-top:10px;">
            <span class="badge neutral">${escapeHtml(String(captureEntry.perceptual_state || "unknown"))}</span>
          </div>
        </div>
        <div class="summary-card">
          <div class="summary-label">Mutation audit</div>
          <div class="summary-value">${escapeHtml(packet.mutation_audit_summary || "No mutation audit summary available.")}</div>
          <div class="summary-list compact" style="margin-top:10px;">
            <span class="badge ${captureEntry.mutation_audit && captureEntry.mutation_audit.successful ? "ok" : "warn"}">${escapeHtml(captureEntry.mutation_audit ? (captureEntry.mutation_audit.successful ? "successful" : "failed") : "none")}</span>
            <span class="badge neutral">${escapeHtml(String(captureEntry.mutation_audit && captureEntry.mutation_audit.risk_level || "n/a"))}</span>
          </div>
        </div>
      `;

      affordanceHighlights.innerHTML = [
        ...safeHighlights.slice(0, 2).map((item) => `<span class="badge ok">${escapeHtml(item)}</span>`),
        ...unsafeHighlights.slice(0, 2).map((item) => `<span class="badge warn">${escapeHtml(item)}</span>`),
        ...reviewOnlyHighlights.slice(0, 2).map((item) => `<span class="badge neutral">${escapeHtml(item)}</span>`),
      ].join("") || `<span class="badge neutral">No affordance highlights.</span>`;
      ownerDistribution.innerHTML = ownerChips || `<span class="badge neutral">No owner distribution.</span>`;
      rawEvidenceRefs.innerHTML = asArray(packet.raw_evidence_refs).map((ref) => `<a class="badge neutral" href="${escapeHtml(ref)}" target="_blank" rel="noreferrer">${escapeHtml(ref)}</a>`).join("") || `<span class="badge neutral">No raw evidence refs.</span>`;

      packetSourceLink.innerHTML = packet.packet_markdown_path
        ? `<a class="badge neutral" href="${escapeHtml(packet.packet_markdown_path)}" target="_blank" rel="noreferrer">${escapeHtml(packet.packet_markdown_path)}</a>`
        : `<span class="badge neutral">No packet source path.</span>`;
      captureManifestJson.textContent = JSON.stringify(captureEntry, null, 2);
      dismissalAuditJson.textContent = JSON.stringify(dismissalEntry, null, 2);
      debugDiagnostics.textContent = JSON.stringify({
        queue_id: packet.queue_id,
        capture_id: packet.capture_id,
        state: captureEntry.perceptual_state || packet.queue_state,
        affordance_owner_distribution: dismissalEntry.affordance_owner_distribution || {},
        affordance_policy_distribution: targetSummary.policyDistribution,
        evidence_count: asArray(packet.raw_evidence_refs).length,
      }, null, 2);
    }

    function renderForm(packet) {
      const draft = state.drafts[packet.queue_id] || packet.review_draft || {};
      reviewerId.value = draft.reviewer_id || "";
      reviewOutcome.value = draft.review_outcome || asArray(packet.allowed_outcomes)[0] || asArray(initialPacket.allowed_outcomes)[0] || "unresolved";
      confidenceBucket.value = draft.confidence_bucket || "unknown";
      reviewNotes.value = draft.notes || "";
      evidenceNotes.value = draft.evidence_notes || "";
      contradictionNotes.value = draft.contradiction_notes || "";
      additionalEvidence.value = draft.additional_evidence_needed || "";
      draftBanner.textContent = state.drafts[packet.queue_id] ? `Local draft stored for ${packet.queue_id}.` : "No local draft stored.";
    }

    function render() {
      const packet = currentPacket();
      renderQueue();
      packetTitle.textContent = packet.brand_name;
      packetSubtitle.textContent = `${packet.category} · ${packet.capture_id} · ${packet.queue_id}`;
      heroBadges.innerHTML = [
        `<span class="badge neutral">${escapeHtml(String(packet.queue_state || "unknown"))}</span>`,
        `<span class="badge neutral">${escapeHtml(String(packet.confidence_bucket || "unknown"))}</span>`,
      ].join("");

      reviewQuestion.textContent = packet.review_decision_required || "Select the most evidence-grounded outcome.";
      outcomeChips.innerHTML = asArray(packet.allowed_outcomes).map((item) => `<span class="badge neutral">${escapeHtml(item)}</span>`).join("");
      requiredFields.innerHTML = asArray(packet.required_fields).map((item) => `<span class="badge neutral">${escapeHtml(item)}</span>`).join("") || `<span class="badge neutral">No required fields.</span>`;
      unresolvedGuidance.innerHTML = asArray(packet.unresolved_handling).map((item) => `<span class="badge neutral">${escapeHtml(item)}</span>`).join("") || `<span class="badge neutral">No unresolved guidance.</span>`;
      contradictionGuidance.innerHTML = asArray(packet.contradiction_handling).map((item) => `<span class="badge neutral">${escapeHtml(item)}</span>`).join("") || `<span class="badge neutral">No contradiction guidance.</span>`;

      renderScreenshots(packet);
      renderEvidenceSummaries(packet);
      renderForm(packet);
    }

    decisionForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const packet = currentPacket();
      state.drafts[packet.queue_id] = {
        reviewer_id: reviewerId.value.trim(),
        review_outcome: reviewOutcome.value,
        confidence_bucket: confidenceBucket.value,
        notes: reviewNotes.value.trim(),
        evidence_notes: evidenceNotes.value.trim(),
        contradiction_notes: contradictionNotes.value.trim(),
        additional_evidence_needed: additionalEvidence.value.trim(),
      };
      renderForm(packet);
    });

    clearDraft.addEventListener("click", () => {
      const packet = currentPacket();
      delete state.drafts[packet.queue_id];
      renderForm(packet);
    });

    render();
  } catch (error) {
    renderError(error);
    if (typeof console !== "undefined" && console.error) {
      console.error("Visual Signature reviewer viewer failed to initialize", error);
    }
  }
})();