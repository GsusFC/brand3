# Brand3 Local Evidence Packet v0 Hardening Review

## Purpose

This review closes the first hardening pass that moved local Evidence Packet v0 closer to the useful Deep Research evidence-packet reference.

The goal was not to add another downstream control layer. The goal was to make the local packet a better pre-narrative ordering layer using existing Brand3 snapshot data only.

## Scope

Updated:

- `src/reports/evidence_packet.py`
- `tests/test_evidence_packet.py`
- `examples/reports/evidence_packet/builtwith_kit_com.local_evidence_packet.v0.json`

Created:

- `docs/brand3_local_evidence_packet_v0_hardening_review.md`
- `docs/brand3_local_evidence_packet_v0_hardening_review.json`

No runtime, prompt, scoring, rendering, persisted payload, Visual Signature, provider, or generation behavior was changed.

## What Changed

Local Evidence Packet v0 now includes:

- `entity_resolution`
- `entity_resolution.related_surfaces`
- `source_inventory` shaped as URL/source records
- `cross_dimension_evidence`
- `cross_dimension_evidence.contradiction_candidates`

Related surfaces now carry:

- `surface`
- `relation_type`
- `relationship`
- `confidence`
- `evidence`
- `requires_human_review`

Source inventory entries now carry:

- `url`
- `source_type`
- `source_quality`
- `role`
- `notes`

The old classification fields remain in place, so downstream lab/review artifacts can still read the same top-level categories.

## Builtwith/Kit Hardened Packet Summary

Regenerated artifact:

`examples/reports/evidence_packet/builtwith_kit_com.local_evidence_packet.v0.json`

Counts after hardening:

| Category | Count |
|---|---:|
| owned claims | 8 |
| external evidence | 5 |
| related surface evidence | 12 |
| technical signals | 1 |
| trust/security signals | 5 |
| visual/internal signals | 2 |
| entity ambiguity | 5 |
| missing evidence | 12 |
| finding-eligible evidence | 0 |
| evidence not eligible for findings | 26 |
| requires human review | 7 |
| source inventory | 27 |

The key result did not change: Builtwith/Kit still has zero finding-eligible evidence under conservative local classification.

That remains the correct result for this case. It shows that the original Brand3 output was generated from evidence that should have been owned-only, technical-only, trust/security review-only, missing-URL, or unresolved related-surface evidence.

## Old Local Packet vs Hardened Packet

The previous local packet already blocked the worst evidence failures:

- visual metrics did not become findings;
- `robots.txt` stayed technical-only;
- trust/security scans stayed review-gated;
- BuiltWith.com remained unresolved related-surface evidence;
- URL-less claims were marked missing.

The hardened packet adds better structure around those decisions:

- explicit entity frame;
- related surfaces grouped with relation metadata;
- source inventory records by URL/source role;
- contradiction candidates for false-merge risks.

This does not make the packet more permissive. It makes the reason for restraint easier to inspect.

## Hardened Packet vs Deep Research Reference

What now matches the Deep Research reference shape:

- entity resolution exists;
- related surfaces are explicit;
- source inventory has URL/source quality/role;
- dimension inputs still preserve classification;
- missing evidence remains first-class;
- contradiction candidates are explicit;
- human review gates stay visible.

What still does not match:

- local v0 cannot discover missing source-context evidence;
- local v0 cannot verify ownership beyond already-collected surfaces;
- local v0 cannot discover canonical related surfaces unless Exa/Web already collected them;
- local v0 cannot judge unfamiliar directories beyond deterministic host/source rules;
- local v0 does not yet create a full nested `dimensions` object matching the reference packet.

The gap is acquisition, not classification.

## Eligibility Hardening

The builder now treats these conservatively:

- owned claims: owned/observation-only unless independently supported;
- marketplace/listing evidence: review-gated by default;
- repository evidence: developer activity only, not adoption;
- trust/security sources: review-gated;
- technical/internal/visual metrics: technical-only;
- usage/install/user-count claims: observation-only unless independently supported;
- missing-URL evidence: not normal finding evidence;
- same-name different-root surfaces: unresolved, not aliases.

This is closer to the reference packet and directly addresses the failure mode where weak or technical evidence becomes strategic prose.

## Contradiction Candidates

The hardening pass adds deterministic contradiction candidates for:

- same-name different-root ambiguity;
- owned claim vs external/related source mixing inside the same feature pool;
- count/activity claims that require support.

These are not findings. They are warning flags for evidence ordering.

For Builtwith/Kit, the most important contradiction candidates are still entity-boundary risks around `builtwith.kit.com` versus `builtwith.com`.

## What Local v0 Can Now Do Cheaply

Local v0 can now cheaply provide:

- a conservative entity frame;
- explicit related-surface records;
- URL/source quality inventory;
- evidence eligibility before generation;
- missing evidence visibility;
- review gates;
- contradiction candidates;
- deterministic blocking of technical, visual, and trust/security signals.

That is enough to prevent many current bad findings before prompt work begins.

## What Still Requires Upstream Enrichment Or Escalation

Local v0 still cannot:

- discover Kit `.kit.com` documentation unless it is collected upstream;
- discover missing canonical related surfaces;
- verify ownership when only weak same-name evidence exists;
- evaluate directory/source authority beyond simple rules;
- resolve hard entity ambiguity;
- turn sparse evidence into clean external validation.

Those tasks belong to improved Exa/Web acquisition or manual/lab Deep Research escalation.

## Readiness To Test On More Snapshots

The hardened packet is ready to test on more existing snapshots.

Suggested next cases:

- Watermelon: should expose related-surface and ecosystem ambiguity with stronger structure.
- LaunchDarkly: should show whether the local packet is too conservative on a cleaner, high-evidence case.

It is not ready to feed into generation.

## Recommended Next Step

Run the hardened Evidence Packet v0 on Watermelon and LaunchDarkly snapshots if available.

The question should be:

Does the packet distinguish clean evidence from ambiguity without blocking everything?

Only after that should Brand3 consider using packet-filtered evidence in narrative generation.

## Non-Goals Preserved

- No runtime integration.
- No prompt changes.
- No scoring changes.
- No report generation changes.
- No rendering changes.
- No persisted payload changes.
- No Visual Signature changes.
- No Deep Research calls.
- No Exa/Firecrawl/API calls.
- No new provider.
- No generation input changes.
