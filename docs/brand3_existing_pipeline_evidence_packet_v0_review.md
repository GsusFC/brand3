# Brand3 Existing Pipeline Evidence Packet v0 Review

## Purpose

This review evaluates the first local/offline Evidence Packet v0 builder against the Builtwith/Kit failure case.

The question is narrow:

> Can Brand3 classify its already-collected Exa/Web/Context evidence before narrative generation, without Deep Research or another provider?

## Artifacts

- Builder: `src/reports/evidence_packet.py`
- Tests: `tests/test_evidence_packet.py`
- Local packet: `examples/reports/evidence_packet/builtwith_kit_com.local_evidence_packet.v0.json`
- Deep Research benchmark: `examples/reports/deep_research_trial/builtwith_kit_com_single_url/evidence_packet.json`

## Implementation Boundary

The builder is offline and snapshot-only.

It reads:

- `run`
- `raw_inputs`
- `features`
- `evidence_items`

It does not call:

- LLMs
- Exa API
- Firecrawl
- Playwright
- Deep Research
- network/web APIs

It does not affect:

- scoring
- prompts
- report generation
- rendering
- persisted payload format
- Visual Signature
- runtime

## Local Packet Summary

For Builtwith run `74`, the local packet produced:

| Category | Count |
|---|---:|
| owned claims | 8 |
| external evidence | 6 |
| related surface evidence | 11 |
| technical signals | 1 |
| trust/security signals | 5 |
| visual/internal signals | 2 |
| entity ambiguity | 4 |
| missing evidence | 12 |
| finding-eligible evidence | 0 |
| evidence not eligible for findings | 26 |
| requires human review | 6 |

The most important result is that the packet produced **zero** finding-eligible evidence for this run.

That is not a failure of the builder. It is the point of the test. The existing Brand3 snapshot does contain many signals, but once source role, entity relation, URL coverage, and eligibility are applied conservatively, the evidence is not clean enough to support normal narrative findings.

## What Matched Deep Research

The local packet matched the Deep Research benchmark on the core failure class:

- Kit claims were treated as owned claims, not external validation.
- BuiltWith.com / blog / KB evidence was treated as unresolved related-surface evidence, not an alias.
- `robots.txt` was technical-only.
- local visual metrics were visual/internal-only.
- Joe Sandbox and ScamAdviser were trust/security review signals.
- URL-less evidence was surfaced as missing evidence.
- no ownership was inferred between `builtwith.kit.com` and `builtwith.com`.

This proves that a useful part of the Deep Research discipline can be approximated locally from existing Brand3 data.

## Where Local v0 Is Weaker Than Deep Research

Deep Research discovered new source-context evidence that the local snapshot does not contain:

- Kit documentation explaining `.kit.com` subdomain behavior.
- BusinessWire/domain-industry evidence about ConvertKit becoming Kit.
- a ConvertKit tracking redirect URL with `utm_campaign=poweredby`.
- a clearer framing of `builtwith.kit.com` as a possible Kit-hosted subdomain or tracking endpoint.

The local builder cannot invent that. It only classifies what Brand3 already collected.

This is the main limitation: local v0 can stop contaminated evidence from becoming findings, but it cannot discover the missing disambiguating evidence.

## Comparison

| Area | Current Brand3 behavior | Local Evidence Packet v0 | Deep Research single-URL packet |
|---|---|---|---|
| Kit owned claims | become repeated findings with caveats | owned, observation-only, URL-missing where applicable | owned/related Kit context separated |
| BuiltWith.com evidence | mixed into normal narrative | unresolved related surface | unresolved related surface plus stronger source-context |
| technical artifacts | can become findings | technical-only | technical/not eligible |
| visual metrics | can become finding | visual/internal-only | not part of packet / not finding evidence |
| trust/security scans | become perception/security findings | review-gated trust/security | review-gated trust/security |
| missing URLs | can survive into findings | explicit `missing_evidence` | citation discipline stronger |
| finding eligibility | prompt receives mixed pool | zero eligible for Builtwith | two eligible source-context items |
| discovery | broad but mixed | none; snapshot-only | strong but expensive |

## What This Means

Evidence Packet v0 changes the diagnosis:

Brand3's current Builtwith output was not merely overwritten by bad prose. It was generated from a pool that should have been mostly blocked or review-gated before narrative generation.

The local packet is therefore useful as a pre-narrative order layer.

But it is not sufficient as acquisition replacement. It does not discover the missing Kit subdomain documentation that made the Deep Research packet stronger.

## Is It Good Enough For Pre-Narrative Evidence Order?

Yes, as an offline diagnostic and likely as a future pre-generation eligibility gate.

No, as a complete evidence acquisition replacement.

The useful split is:

- local Evidence Packet v0 for default deterministic classification and blocking;
- optional/manual Deep Research or targeted Exa/Web enrichment only when the local packet detects unresolved entity ambiguity or too little eligible evidence.

## What Should Remain Review-Gated

- same-name different-root domains;
- trust/security scanner interpretations;
- URL-less owned claims;
- social profile candidates with no verification or activity;
- BuiltWith.com evidence in a `builtwith.kit.com` audit;
- visual/internal metrics;
- technical readiness artifacts.

## Downstream Impact

If this packet is eventually inserted before findings generation, several downstream controls should shrink:

- missing-evidence Narrative Harness warnings should drop;
- safe-attribution repetition should drop because owned claims can be centralized or blocked;
- EntityNarrativeState should consume explicit ambiguity instead of reconstructing it from prose;
- Lab recomposition should become less necessary;
- render suppression should be a last resort, not the main fix.

## Recommended Next Step

Do not feed the packet into generation yet.

Next step:

**Run Evidence Packet v0 on two more existing snapshots: one clean/high-evidence case and one ambiguous case.**

The goal is to test whether v0 is too conservative globally, or correctly conservative only on Builtwith.

Suggested cases:

- LaunchDarkly: should produce some eligible external evidence.
- Iris or Watermelon: should produce ambiguity/review gates without false aliases.

Only after that should Brand3 consider wiring packet-filtered evidence into the narrative prompt.

## Non-Goals Preserved

- No runtime integration.
- No prompt changes.
- No scoring changes.
- No report generation changes.
- No rendering changes.
- No payload changes.
- No Visual Signature changes.
- No Deep Research call.
- No Exa/Firecrawl/API call.
