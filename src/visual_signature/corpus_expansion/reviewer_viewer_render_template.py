"""Template renderer for Visual Signature reviewer viewer."""

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
""".strip()

