"""Static local viewer for the Visual Signature reviewer workflow pilot."""

from __future__ import annotations

import html
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.visual_signature.corpus_expansion.reviewer_packets import build_reviewer_packets
from src.visual_signature.corpus_expansion.reviewer_packets import validate_reviewer_packets


REVIEWER_VIEWER_SCHEMA_VERSION = "visual-signature-reviewer-viewer-1"
REVIEWER_VIEWER_RECORD_TYPE = "reviewer_viewer_bundle"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "examples" / "visual_signature" / "corpus_expansion" / "reviewer_viewer"
DEFAULT_REVIEWER_WORKFLOW_PILOT_PATH = PROJECT_ROOT / "examples" / "visual_signature" / "corpus_expansion" / "reviewer_workflow_pilot.json"
DEFAULT_REVIEW_QUEUE_PATH = PROJECT_ROOT / "examples" / "visual_signature" / "corpus_expansion" / "review_queue.json"
DEFAULT_CAPTURE_MANIFEST_PATH = PROJECT_ROOT / "examples" / "visual_signature" / "screenshots" / "capture_manifest.json"
DEFAULT_DISMISSAL_AUDIT_PATH = PROJECT_ROOT / "examples" / "visual_signature" / "screenshots" / "dismissal_audit.json"
DEFAULT_PACKETS_ROOT = PROJECT_ROOT / "examples" / "visual_signature" / "corpus_expansion" / "reviewer_packets"


def build_reviewer_viewer_bundle(
    *,
    reviewer_workflow_pilot_path: str | Path = DEFAULT_REVIEWER_WORKFLOW_PILOT_PATH,
    review_queue_path: str | Path = DEFAULT_REVIEW_QUEUE_PATH,
    capture_manifest_path: str | Path = DEFAULT_CAPTURE_MANIFEST_PATH,
    dismissal_audit_path: str | Path = DEFAULT_DISMISSAL_AUDIT_PATH,
    packets_root: str | Path = DEFAULT_PACKETS_ROOT,
    output_root: str | Path | None = None,
) -> dict[str, Any]:
    output_root = Path(output_root) if output_root is not None else DEFAULT_OUTPUT_ROOT
    pilot_payload = _load_json(reviewer_workflow_pilot_path)
    review_queue_payload = _load_json(review_queue_path)
    capture_manifest_payload = _load_json(capture_manifest_path)
    dismissal_audit_payload = _load_json(dismissal_audit_path)
    packets_payload = build_reviewer_packets(reviewer_workflow_pilot_path=reviewer_workflow_pilot_path, output_root=packets_root)
    packet_rows = packets_payload["packets"]

    selected_ids = pilot_payload.get("selected_review_queue_item_ids", [])
    queue_item_map = {item.get("queue_id"): item for item in review_queue_payload.get("queue_items", [])}
    packet_map = {packet["queue_id"]: packet for packet in packet_rows}
    capture_map = {entry.get("brand_name"): entry for entry in capture_manifest_payload.get("results", [])}
    dismissal_map = {entry.get("brand_name"): entry for entry in dismissal_audit_payload.get("results", [])}

    packets: list[dict[str, Any]] = []
    for queue_id in selected_ids:
        packet = packet_map.get(queue_id)
        queue_item = queue_item_map.get(queue_id, {})
        if not packet:
            continue
        capture_id = str(packet["capture_id"])
        packet_markdown_path = Path(packets_root) / f"{capture_id}.md"
        capture_entry = capture_map.get(str(packet["brand_name"]), {})
        dismissal_entry = dismissal_map.get(str(packet["brand_name"]))
        packets.append(
            {
                "queue_id": queue_id,
                "capture_id": capture_id,
                "brand_name": packet["brand_name"],
                "category": packet["category"],
                "queue_state": packet["queue_state"],
                "confidence_bucket": queue_item.get("confidence_bucket"),
                "screenshot_paths": [_to_viewer_relative_path(path, viewer_root=output_root) for path in packet["screenshot_paths"]],
                "raw_evidence_refs": [_to_viewer_relative_path(path, viewer_root=output_root) for path in packet["raw_evidence_refs"]],
                "obstruction_summary": packet["obstruction_summary"],
                "affordance_summary": packet["affordance_summary"],
                "perceptual_state_summary": packet["perceptual_state_summary"],
                "mutation_audit_summary": packet["mutation_audit_summary"],
                "packet_markdown_path": _to_viewer_relative_path(packet_markdown_path, viewer_root=output_root),
                "capture_manifest_entry": _summarize_capture_entry(capture_entry, viewer_root=output_root),
                "dismissal_audit_entry": _summarize_dismissal_entry(dismissal_entry),
                "review_instructions": list(pilot_payload.get("review_instructions", [])),
                "required_reviewer_fields": list(pilot_payload.get("required_reviewer_fields", [])),
                "allowed_review_outcomes": list(pilot_payload.get("allowed_review_outcomes", [])),
                "unresolved_handling": list(pilot_payload.get("unresolved_handling", [])),
                "contradiction_handling": list(pilot_payload.get("contradiction_handling", [])),
                "reviewer_coverage_requirements": list(pilot_payload.get("reviewer_coverage_requirements", [])),
                "explicit_note": "Do not invent evidence.",
                "review_draft": {
                    "reviewer_id": "",
                    "review_outcome": "unresolved",
                    "confidence_bucket": "unknown",
                    "notes": "",
                },
            }
        )

    payload = {
        "schema_version": REVIEWER_VIEWER_SCHEMA_VERSION,
        "record_type": REVIEWER_VIEWER_RECORD_TYPE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "readiness_scope": pilot_payload.get("readiness_scope", "human_review_scaling"),
        "pilot_run_id": pilot_payload.get("pilot_run_id"),
        "pilot_status": pilot_payload.get("pilot_status"),
        "review_queue_path": _to_viewer_relative_path(review_queue_path, viewer_root=output_root),
        "reviewer_workflow_pilot_path": _to_viewer_relative_path(reviewer_workflow_pilot_path, viewer_root=output_root),
        "capture_manifest_path": _to_viewer_relative_path(capture_manifest_path, viewer_root=output_root),
        "dismissal_audit_path": _to_viewer_relative_path(dismissal_audit_path, viewer_root=output_root),
        "reviewer_packets_root": _to_viewer_relative_path(Path(packets_root), viewer_root=output_root),
        "packet_count": len(packets),
        "selected_review_queue_item_ids": selected_ids,
        "packets": packets,
        "navigation_help": [
            "Use the left rail to switch queue items.",
            "Use the decision form for local draft notes only.",
            "No draft is persisted to disk.",
            "Do not invent evidence.",
        ],
        "non_goals": [
            "no scoring integration",
            "no runtime enablement",
            "no production UI integration",
            "no provider execution",
            "no model-training integration",
            "no capture behavior changes",
        ],
        "source_artifacts": [
            _to_viewer_relative_path(reviewer_workflow_pilot_path, viewer_root=output_root),
            _to_viewer_relative_path(review_queue_path, viewer_root=output_root),
            _to_viewer_relative_path(capture_manifest_path, viewer_root=output_root),
            _to_viewer_relative_path(dismissal_audit_path, viewer_root=output_root),
            _to_viewer_relative_path(Path(packets_root) / "allbirds.md", viewer_root=output_root),
            _to_viewer_relative_path(Path(packets_root) / "headspace.md", viewer_root=output_root),
        ],
        "notes": [
            "Evidence-only local reviewer viewer.",
            "Scope separation and readiness semantics are preserved.",
        ],
    }
    return payload


def validate_reviewer_viewer_bundle(
    *,
    viewer_root: str | Path,
    reviewer_workflow_pilot_path: str | Path = DEFAULT_REVIEWER_WORKFLOW_PILOT_PATH,
    review_queue_path: str | Path = DEFAULT_REVIEW_QUEUE_PATH,
    capture_manifest_path: str | Path = DEFAULT_CAPTURE_MANIFEST_PATH,
    dismissal_audit_path: str | Path = DEFAULT_DISMISSAL_AUDIT_PATH,
    packets_root: str | Path = DEFAULT_PACKETS_ROOT,
) -> list[str]:
    viewer_root = Path(viewer_root)
    errors: list[str] = []
    required_files = ["index.html", "viewer.css", "viewer.js"]
    for name in required_files:
        if not (viewer_root / name).exists():
            errors.append(f"missing viewer file: {name}")

    packet_errors = validate_reviewer_packets(
        reviewer_workflow_pilot_path=reviewer_workflow_pilot_path,
        packets_root=packets_root,
    )
    errors.extend(packet_errors)
    if packet_errors:
        return errors

    payload = build_reviewer_viewer_bundle(
        reviewer_workflow_pilot_path=reviewer_workflow_pilot_path,
        review_queue_path=review_queue_path,
        capture_manifest_path=capture_manifest_path,
        dismissal_audit_path=dismissal_audit_path,
        packets_root=packets_root,
        output_root=viewer_root,
    )
    if payload["packet_count"] != len(payload["packets"]):
        errors.append("packet_count does not match packet list length")
    if set(payload["selected_review_queue_item_ids"]) != {packet["queue_id"] for packet in payload["packets"]}:
        errors.append("selected_review_queue_item_ids do not match packets")
    if any(packet["queue_state"] not in {"queued", "needs_additional_evidence"} for packet in payload["packets"]):
        errors.append("viewer includes non-pending queue states")
    for packet in payload["packets"]:
        packet_path = Path(packet["packet_markdown_path"])
        resolved_packet_path = viewer_root / packet_path
        if not resolved_packet_path.exists():
            errors.append(f"missing packet markdown: {packet['packet_markdown_path']}")
        else:
            packet_markdown = _read_text(resolved_packet_path)
            if "Do not invent evidence." not in packet_markdown:
                errors.append(f"packet missing evidence warning: {packet['queue_id']}")
        if not packet["screenshot_paths"]:
            errors.append(f"packet missing screenshot paths: {packet['queue_id']}")
    return errors


def write_reviewer_viewer_bundle(
    *,
    output_root: str | Path | None = None,
    reviewer_workflow_pilot_path: str | Path = DEFAULT_REVIEWER_WORKFLOW_PILOT_PATH,
    review_queue_path: str | Path = DEFAULT_REVIEW_QUEUE_PATH,
    capture_manifest_path: str | Path = DEFAULT_CAPTURE_MANIFEST_PATH,
    dismissal_audit_path: str | Path = DEFAULT_DISMISSAL_AUDIT_PATH,
    packets_root: str | Path = DEFAULT_PACKETS_ROOT,
) -> dict[str, str]:
    viewer_root = Path(output_root) if output_root is not None else DEFAULT_OUTPUT_ROOT
    viewer_root.mkdir(parents=True, exist_ok=True)
    packet_errors = validate_reviewer_packets(
        reviewer_workflow_pilot_path=reviewer_workflow_pilot_path,
        packets_root=packets_root,
    )
    if packet_errors:
        raise ValueError(f"reviewer packet validation failed: {packet_errors}")
    payload = build_reviewer_viewer_bundle(
        reviewer_workflow_pilot_path=reviewer_workflow_pilot_path,
        review_queue_path=review_queue_path,
        capture_manifest_path=capture_manifest_path,
        dismissal_audit_path=dismissal_audit_path,
        packets_root=packets_root,
        output_root=viewer_root,
    )
    _write_text(viewer_root / "index.html", _render_index_html(payload))
    _write_text(viewer_root / "viewer.css", _viewer_css())
    _write_text(viewer_root / "viewer.js", _viewer_js())
    return {
        "viewer_root": str(viewer_root),
        "viewer_index_html": str(viewer_root / "index.html"),
        "viewer_css": str(viewer_root / "viewer.css"),
        "viewer_js": str(viewer_root / "viewer.js"),
    }


def _render_index_html(payload: dict[str, Any]) -> str:
    embedded = html.escape(json.dumps(payload, ensure_ascii=False), quote=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Visual Signature Reviewer Viewer</title>
  <link rel="stylesheet" href="./viewer.css">
</head>
<body>
  <div id="app" class="page">
    <pre class="term-head"><span class="prompt">❯</span> visual-signature-reviewer <span class="hl-accent">--scope</span> {html.escape(str(payload.get("readiness_scope", "human_review_scaling")))} <span class="dim">· offline evidence-only</span></pre>
    <hr class="rule">
    <section class="fallback-main static-skeleton">
      <div class="card">
        <h1>Visual Signature Reviewer Viewer</h1>
        <div class="viewer-fallback">
          <strong>Loading reviewer packet bundle…</strong>
          <div class="muted">Visible fallback panel. If JavaScript fails, this static local-only state remains readable.</div>
        </div>
      </div>
    </section>
    <script id="viewer-data" type="application/json">{embedded}</script>
  </div>
  <script src="./viewer.js" defer></script>
</body>
</html>
"""


def _viewer_css() -> str:
    return """
:root {
  color-scheme: light;
  --bg: #eeeeee;
  --panel: #f5f5f5;
  --panel-2: #f0f0f0;
  --panel-3: #f7f7f7;
  --rule: #e4e4e4;
  --border: #e4e4e4;
  --text: #111111;
  --muted: #6b6b6b;
  --accent: #ef490d;
  --key: #6b6b6b;
  --good: #1f5d3a;
  --warn: #9a7a00;
  --bad: #a8261c;
  --radius: 2px;
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
  line-height: 1.55;
  font-feature-settings: "liga" 0, "calt" 0;
  text-rendering: geometricPrecision;
  -webkit-font-smoothing: antialiased;
}
body { min-height: 100vh; }
a {
  color: inherit;
  text-decoration: underline;
  text-decoration-color: rgba(239, 73, 13, 0.58);
  text-underline-offset: 3px;
}
a:hover {
  color: var(--text);
  text-decoration-color: var(--accent);
}
button, input, select, textarea { font: inherit; }
.page {
  width: min(1440px, calc(100% - 56px));
  min-height: calc(100vh - 48px);
  margin: 24px auto;
  background: rgba(245, 245, 245, 0.94);
  border: 1px solid var(--rule);
  box-shadow: 0 10px 32px rgba(22, 22, 22, 0.035);
}
.viewer-workspace {
  padding: 28px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 28px;
  align-items: start;
}
.card, .details-panel, .hero {
  background: var(--panel);
  border: 1px solid var(--rule);
  border-radius: var(--radius);
}
.main {
  display: grid;
  gap: 18px;
}
.fallback-main {
  max-width: 720px;
  width: 100%;
  padding: 28px;
}
.right-panel {
  display: grid;
  gap: 18px;
  position: sticky;
  top: 40px;
}
.brand-block h1, .hero h2, .card h3 {
  margin: 0;
}
.brand-block h1 { font-size: 16px; line-height: 1.2; }
.term-head {
  min-height: 44px;
  display: flex;
  align-items: center;
  white-space: pre-wrap;
  margin: 0;
  padding: 0 28px;
  border-bottom: 1px solid var(--rule);
  background: rgba(238, 238, 238, 0.76);
  font-size: 12px;
  line-height: 1.5;
}
.prompt {
  color: var(--accent);
  user-select: none;
  font-weight: 700;
}
.hl-accent { color: var(--accent); }
.dim { color: var(--muted); }
.hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px;
}
.hero h2 { font-size: 18px; margin-top: 6px; }
.hero .subtle, .muted, .small, .meta { color: var(--muted); }
.eyebrow { text-transform: uppercase; letter-spacing: 0.08em; font-size: 11px; color: var(--key); }
.badge-line { display: flex; flex-wrap: wrap; gap: 8px; }
.badge, .status-badge, .scope-badge, .pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--rule);
  background: var(--panel);
  border-radius: var(--radius);
  padding: 4px 8px;
  color: var(--text);
  font-size: 12px;
  line-height: 1;
}
.badge.ok { border-color: rgba(31, 93, 58, 0.35); color: var(--good); }
.badge.warn { border-color: rgba(154, 122, 0, 0.35); color: var(--warn); }
.badge.bad { border-color: rgba(168, 38, 28, 0.35); color: var(--bad); }
.badge.neutral { color: var(--text); }
.queue-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.queue-item {
  text-align: left;
  border: 1px solid var(--rule);
  background: var(--panel);
  color: var(--text);
  border-radius: var(--radius);
  padding: 7px 10px;
  cursor: pointer;
}
.queue-item.active { border-color: var(--accent); color: var(--accent); background: var(--panel-2); }
.queue-item .title { display: flex; justify-content: space-between; gap: 12px; font-weight: 600; }
.queue-item .sub { color: var(--muted); font-size: 12px; margin-top: 4px; }
.queue-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 2px;
}
.section-card, .summary-card, .card, .details-panel {
  padding: 16px;
}
.rule {
  border: 0;
  border-top: 1px solid var(--rule);
  margin: 0;
}
.rule-thin {
  border: 0;
  border-top: 1px dashed var(--rule);
  margin: 24px 0;
}
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 18px;
  margin: 0 0 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--rule);
}
.section-head .label {
  color: var(--text);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.section-head .tag {
  color: var(--muted);
  font-size: 12px;
  font-weight: 400;
  text-align: right;
}
.card-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
}
.card-head p { margin: 6px 0 0; color: var(--muted); font-size: 13px; }
.screenshot-card .card-head {
  margin-bottom: 10px;
}
.screenshot-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.tab-button {
  border: 1px solid var(--rule);
  background: var(--panel-2);
  color: var(--text);
  border-radius: var(--radius);
  padding: 7px 10px;
  cursor: pointer;
}
.tab-button.active { border-color: var(--accent); color: var(--accent); }
.screenshot-stage {
  background: #ffffff;
  border: 1px solid var(--rule);
  border-radius: var(--radius);
  overflow: hidden;
}
.screenshot-stage img {
  display: block;
  width: 100%;
  max-height: 720px;
  object-fit: contain;
  background: #ffffff;
}
.screenshot-stage.full-page img {
  max-height: none;
}
.screenshot-fallback {
  min-height: 340px;
  display: grid;
  place-items: center;
  gap: 10px;
  padding: 32px;
  color: var(--muted);
  text-align: center;
}
.screenshot-fallback strong { color: var(--text); }
.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.summary-card {
  background: var(--panel);
  border: 1px solid var(--rule);
  border-radius: var(--radius);
}
.summary-label {
  color: var(--key);
  font-size: 12px;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.summary-value {
  white-space: pre-wrap;
  line-height: 1.45;
  color: var(--text);
  font-size: 14px;
}
.summary-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.summary-list.compact .badge { padding: 4px 8px; }
.review-question .question {
  font-size: 16px;
  line-height: 1.5;
  color: var(--text);
}
.review-question .question-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.decision-form {
  display: grid;
  gap: 12px;
}
.form-row {
  display: grid;
  gap: 8px;
}
.form-row label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; }
.form-row input, .form-row select, .form-row textarea {
  width: 100%;
  background: var(--panel-3);
  color: var(--text);
  border: 1px solid var(--rule);
  border-radius: var(--radius);
  padding: 10px 12px;
}
.form-row textarea { min-height: 94px; resize: vertical; }
.button-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.button {
  min-height: 42px;
  border: 1px solid var(--text);
  background: var(--text);
  color: #f5f5f5;
  border-radius: 0;
  padding: 10px 16px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.button:hover { background: var(--accent); border-color: var(--accent); }
.button.primary { border-color: var(--text); color: #f5f5f5; }
.draft-banner {
  font-size: 12px;
  color: var(--muted);
}
.details-panel {
  background: var(--panel);
}
.details-panel > summary {
  cursor: pointer;
  list-style: none;
  font-weight: 600;
  color: var(--text);
}
.details-panel > summary::-webkit-details-marker { display: none; }
.details-body { display: grid; gap: 14px; margin-top: 12px; }
.two-col {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.compact-block {
  padding: 12px;
  border: 1px solid var(--rule);
  border-radius: var(--radius);
  background: var(--panel-3);
}
.compact-block h4 {
  margin: 0 0 8px;
  font-size: 13px;
}
.compact-block pre, .raw-json {
  white-space: pre-wrap;
  overflow: auto;
  margin: 0;
  padding: 12px;
  border-radius: var(--radius);
  background: #fafafa;
  border: 1px solid var(--rule);
  color: var(--text);
  max-height: 280px;
}
.viewer-fallback {
  border: 1px dashed var(--rule);
  border-radius: var(--radius);
  background: var(--panel-3);
  padding: 12px;
  color: var(--text);
}
.static-skeleton .muted { color: var(--muted); }
.static-skeleton { pointer-events: none; }
.viewer-error {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px;
}
.viewer-error-card {
  max-width: 720px;
  border: 1px solid var(--bad);
  background: var(--panel);
  border-radius: var(--radius);
  padding: 20px;
}
.viewer-error-card h1 {
  margin: 0 0 8px;
  font-size: 20px;
}
.viewer-error-card pre {
  white-space: pre-wrap;
  overflow: auto;
  margin: 12px 0 0;
  padding: 12px;
  border-radius: var(--radius);
  background: #fafafa;
  border: 1px solid var(--rule);
  color: var(--bad);
}
.summary-divider {
  margin: 0;
  border: 0;
  border-top: 1px solid var(--rule);
}
.kv {
  display: grid;
  grid-template-columns: 160px 1fr;
  row-gap: 4px;
  column-gap: 14px;
  font-family: var(--font-mono);
}
.kv .k { color: var(--accent); }
.kv .v { color: var(--text); }
.footer {
  margin-top: 0;
  padding: 18px 28px 24px;
  border-top: 1px solid var(--rule);
  background: rgba(238, 238, 238, 0.7);
  color: var(--muted);
  font-size: 12px;
}
.footer-note, .footer-cursor { margin-top: 12px; }
.cursor {
  display: inline-block;
  width: 7px;
  height: 14px;
  background: var(--accent);
  vertical-align: -2px;
  animation: blink 1.05s steps(1, end) infinite;
  margin-left: 4px;
}
@keyframes blink { 0%, 55% { opacity: 1; } 56%, 100% { opacity: 0; } }
@media (max-width: 1180px) {
  .viewer-workspace { grid-template-columns: 1fr; }
  .right-panel { position: static; }
}
@media (max-width: 980px) {
  .page { width: min(100% - 32px, 760px); margin-top: 16px; }
  .viewer-workspace { padding: 18px; grid-template-columns: 1fr; gap: 18px; }
  .right-panel { position: static; }
  .queue-strip { align-items: flex-start; flex-direction: column; }
  .summary-grid, .two-col { grid-template-columns: 1fr; }
}
""".strip()


def _viewer_js() -> str:
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
""".strip()


def _summarize_capture_entry(entry: dict[str, Any] | None, *, viewer_root: str | Path) -> dict[str, Any]:
    if not entry:
        return {}
    summary = {
        "capture_id": entry.get("capture_id"),
        "brand_name": entry.get("brand_name"),
        "dismissal_attempted": entry.get("dismissal_attempted"),
        "dismissal_eligibility": entry.get("dismissal_eligibility"),
        "dismissal_block_reason": entry.get("dismissal_block_reason"),
        "dismissal_successful": entry.get("dismissal_successful"),
        "perceptual_state": entry.get("perceptual_state"),
        "raw_screenshot_path": entry.get("raw_screenshot_path"),
        "clean_attempt_screenshot_path": entry.get("clean_attempt_screenshot_path"),
        "raw_viewport_metrics": entry.get("raw_viewport_metrics"),
        "clean_attempt_metrics": entry.get("clean_attempt_metrics"),
        "candidate_click_targets": _summarize_click_targets(entry.get("candidate_click_targets", [])),
        "rejected_click_targets": _summarize_click_targets(entry.get("rejected_click_targets", [])),
        "mutation_audit": entry.get("mutation_audit"),
        "evidence_integrity_notes": entry.get("evidence_integrity_notes", []),
    }
    for key in ("raw_screenshot_path", "clean_attempt_screenshot_path", "screenshot_path", "secondary_screenshot_path"):
        if summary.get(key):
            summary[key] = _to_viewer_relative_path(summary[key], viewer_root=viewer_root)
    mutation_audit = summary.get("mutation_audit")
    if isinstance(mutation_audit, dict):
        for key in ("before_artifact_ref", "after_artifact_ref"):
            if mutation_audit.get(key):
                mutation_audit[key] = _to_viewer_relative_path(mutation_audit[key], viewer_root=viewer_root)
    return summary


def _summarize_click_targets(targets: Any) -> list[dict[str, Any]]:
    if not isinstance(targets, list):
        return []
    compact_targets: list[dict[str, Any]] = []
    for target in targets:
        if not isinstance(target, dict):
            continue
        compact_targets.append(
            {
                "label": target.get("label"),
                "affordance_category": target.get("affordance_category"),
                "affordance_confidence": target.get("affordance_confidence"),
                "affordance_owner": target.get("affordance_owner"),
                "owner_confidence": target.get("owner_confidence"),
                "interaction_policy": target.get("interaction_policy"),
                "method": target.get("method"),
                "reason": target.get("reason"),
            }
        )
    return compact_targets


def _summarize_dismissal_entry(entry: dict[str, Any] | None) -> dict[str, Any]:
    if not entry:
        return {}
    return {
        "brand_name": entry.get("brand_name"),
        "dismissal_attempted": entry.get("dismissal_attempted"),
        "dismissal_successful": entry.get("dismissal_successful"),
        "dismissal_method": entry.get("dismissal_method"),
        "clicked_text": entry.get("clicked_text"),
        "before_severity": entry.get("before_obstruction", {}).get("severity"),
        "after_severity": entry.get("after_obstruction", {}).get("severity"),
        "affordance_owner_distribution": entry.get("affordance_owner_distribution", {}),
    }


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _to_viewer_relative_path(path: str | Path, *, viewer_root: str | Path) -> str:
    viewer_root = Path(viewer_root)
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return os.path.relpath(candidate.resolve(), viewer_root)
