# Per-Audit Brand3 Lab Architecture Goal

Purpose:
Define how every Brand Audit can have an associated Brand3 Lab case where experimental/research layers can be loaded, inspected, and compared without changing the official Brand Audit output.

Objective:
Move Brand3 Lab from a mostly static research/example area into a modular per-audit inspection layer.

Brand Audit remains official:
- scores
- report
- findings
- evidence
- public result page

Brand3 Lab becomes the research/review layer attached to each audit:
- narrative diagnostics
- render-aware diagnostics
- EntityNarrativeState
- state-aware findings comparison
- perceptual signal classification
- overreach checks
- editorial discipline checks
- optional future perceptual layers

Create:
- `docs/brand3_per_audit_lab_architecture.md`
- `docs/brand3_per_audit_lab_architecture.json`

Read:
- `web/routes/brand3_lab.py`
- `web/brand3_lab_data.py`
- `web/templates/brand3_lab*.j2`
- `web/routes/report.py`
- `web/routes/brand.py`
- `src/reports/narrative_harness.py`
- `src/reports/entity_narrative_state.py`
- `docs/brand3_narrative_composition_artifact_index.md`
- `docs/brand3_builder_hardening_phase_close.md`
- current Lab example artifacts under `examples/reports/narrative_harness/`

Define:
1. Relationship model between Brand Audit and per-audit Lab cases.
2. Lab layer model and modular layer list.
3. Layer activation model: required inputs, optional inputs, unavailable/manual/generated states.
4. Data contract for reading reports, evidence, diagnostics, entity state and future perceptual artifacts.
5. UI route architecture:
   - `/brand3-lab`
   - `/brand3-lab/cases`
   - `/brand3-lab/cases/{run_id_or_slug}`
   - `/brand3-lab/cases/{run_id_or_slug}/layers/{layer_id}`
6. Links from official report to Lab case and back.
7. Separation rules protecting scoring, reports, prompts, Visual Signature and runtime.
8. Smallest safe first implementation slice.
9. Risks and mitigations.
10. Future tests/invariants.

Constraints:
- Documentation/specification only.
- Do not implement routes.
- Do not modify templates.
- Do not modify scoring.
- Do not modify prompts.
- Do not modify report generation.
- Do not modify rendering.
- Do not modify persisted payload format.
- Do not modify Visual Signature.
- Do not wire Narrative Harness or EntityNarrativeState into production runtime.
- Do not call LLMs.

Validation:
- `jq -e docs/brand3_per_audit_lab_architecture.json`
- `git diff --check`
