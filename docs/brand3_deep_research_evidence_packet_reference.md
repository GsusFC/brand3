# Brand3 Deep Research Evidence Packet Reference

## Purpose

This memo records the useful shape from the Watermelon single-URL Deep Research trial that produced a structured evidence packet in a separate manual/Codex run.

It is not a production integration plan.

The useful result was not better prose. The useful result was better ordering:

1. start from one audit URL;
2. resolve entity and related surfaces first;
3. classify sources before dimensions;
4. classify evidence by Brand3 dimension;
5. compute finding eligibility before narrative;
6. mark gaps, ambiguity, and review gates explicitly.

## Reference Target

Target URL:

`https://watermelon.sh`

The reference output treated the audited URL as the only seed, then discovered related surfaces through URL context and search.

## Reference Contract

The working contract was stricter than the failed Watermelon prism trial.

It required:

- JSON only;
- no Brand Audit prose;
- no scoring;
- no strategy recommendations;
- no findings;
- no marketing analysis;
- explicit entity resolution;
- source inventory;
- dimension-level evidence buckets;
- cross-dimension evidence buckets;
- missing evidence;
- source quality notes;
- cost risk notes.

The key difference was that each evidence item had to carry its own classification:

- `source_type`
- `evidence_strength`
- `entity_relation`
- `eligible_for_finding`
- `limits`
- `requires_human_review`

That made the output useful as input order, not as a report.

## Required Shape

The reference top-level structure was:

- `case_id`
- `target_url`
- `entity_resolution`
- `source_inventory`
- `dimensions`
- `cross_dimension_evidence`
- `evidence_gaps`
- `source_quality_notes`
- `cost_risk_notes`

Each dimension used the same buckets:

- `owned_claims`
- `external_evidence`
- `related_surface_evidence`
- `technical_signals`
- `trust_or_security_signals`
- `finding_eligible_evidence`
- `evidence_not_eligible_for_findings`
- `missing_evidence`
- `requires_human_review`

This is materially better than sending a flat evidence pool into finding generation.

## What The Reference Output Did Well

The Watermelon reference packet did several things Brand3 currently needs:

- treated `watermelon.sh` as the audited surface;
- separated `ui.watermelon.sh` as an explicitly linked product surface;
- separated `studio.watermelon.sh` as explicitly linked but still requiring review because fetch evidence was weaker;
- treated `github.com/WatermelonCorp` as related only because the audited surface linked to GitHub;
- treated repository evidence as developer-surface evidence, not broad market proof;
- kept marketplace listings as medium-quality external/directory evidence;
- blocked unrelated `watermelon.ai` and `watermelontools` surfaces from becoming aliases;
- preserved entity ambiguities such as email mismatch and component-count mismatch;
- marked unsupported usage/install claims as not finding-eligible;
- kept missing evidence explicit.

This is the first output that looks like a plausible upstream evidence contract for Brand3.

## Important Corrections

The reference output is not production-safe as-is.

Several classifications should remain conservative:

- `confidence: high` for primary entity may be too strong when based mostly on owned links and GitHub metadata.
- Marketplace listings should usually be `observation_only` or medium-confidence evidence, not strong finding evidence.
- Blog/directory commentary can support category placement, but not quality, traction, or differentiation superiority.
- Repository activity can support developer activity, but not adoption.
- Usage claims such as `500+ daily users`, `50k+ installs`, and `500+ vibe coders` should remain not eligible unless independently verified.

The reference packet is valuable because it exposes these distinctions, not because every classification is final.

## Contrast With Failed Watermelon Prism Trial

The failed local Deep Research prism trial returned a narrative audit instead of JSON.

That failure showed the same risk Brand3 already has:

evidence acquisition becomes interpretation too early.

The reference packet avoided most of that by forcing JSON buckets and item-level eligibility fields.

The lesson is not "use Deep Research by default."

The lesson is:

Brand3 needs a strict Information-to-Evidence Contract before any finding generation.

## Role In Brand3

This reference should be used as:

- a benchmark for Evidence Packet v0;
- a design target for existing Exa/Web acquisition ordering;
- a manual/lab escalation example for hard entity ambiguity;
- a prompt-contract reference if Deep Research is tested again.

It should not be used as:

- production report input;
- scoring input;
- proof that Deep Research should replace collectors;
- a runtime dependency;
- a direct prompt rollout;
- a generated finding source.

## Recommended Use

Use this reference to harden the local Evidence Packet v0:

- add target-surface entity resolution before dimensions;
- preserve explicit related-surface relation types;
- preserve source inventory and source quality;
- keep marketplace/repository evidence in bounded roles;
- make `eligible_for_finding` conservative and auditable;
- require missing evidence to be first-class;
- keep human review gates visible.

The next useful comparison is field-by-field:

Deep Research reference packet vs local Evidence Packet v0.

