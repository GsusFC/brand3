# Brand3 Existing Pipeline Evidence Reset Plan

## Purpose

This plan resets the first half of Brand3 around evidence order instead of adding more downstream narrative controls.

Brand3 already has enough acquisition machinery:

- Exa for search, mentions, competitors, news, AI visibility, discovery preview, and enrichment.
- WebCollector for owned page reading through Firecrawl plus local HTML/browser fallbacks.
- Context collection for technical readiness.
- Playwright as the default screenshot path.

The problem is not lack of providers. The problem is that collected information becomes narrative evidence before it has been classified for source role, entity relation, and finding eligibility.

Core question:

> Can Brand3 produce a cleaner evidence packet from existing Exa + WebCollector inputs before findings generation, so the model no longer has to rationalize mixed or noisy evidence?

Answer: yes, but only if the reset happens before `src/reports/derivation.py::collect_evidences()` feeds report findings.

## Current Acquisition Flow

| Stage | Current file | Input | Output | Evidence risk |
|---|---|---|---|---|
| Audit URL | `brand_service.analyze_brand` | submitted URL + brand name | run record | none |
| Context scan | `input_collection._collect_context_input` | audit URL | `ContextData`, context `evidence_items` | technical artifacts can later look like narrative evidence |
| Web scrape | `input_collection._collect_web_input` → `WebCollector.scrape` | audit URL | `WebData` markdown/html/links/images/tech | owned content, fallback content, and scrape artifacts share one shape |
| Exa collection | `input_collection._collect_exa_input` → `ExaCollector.collect_brand_data` | brand name + effective URL | mentions, competitors, news, AI visibility | search results can include same-name/off-entity surfaces |
| Social/competitor inputs | `input_collection` + collectors | brand/content/search data | social + competitor payloads | comparative context can leak into brand narrative |
| Discovery preview | `discovery.evidence_preview` | Exa/Web/Context | owned/third-party domain counts | only preview; not a hard evidence gate |
| Discovery enrichment | `discovery.enrichment` | planned URLs/queries | merged WebData/ExaData | added results are merged back into normal inputs |
| Feature extraction | `services.feature_pipeline` + feature modules | raw inputs | features with `raw_value`, confidence, source | feature raw values become evidence containers |
| Evidence items | context + storage | technical/context facts | persisted `evidence_items` | confidence/freshness exist but are not prompt-visible enough |
| Narrative evidence | `reports.derivation.collect_evidences` | features + evidence_items | flat `Evidence` objects by dimension | source role and eligibility are flattened |
| Finding generation | `reports.narrative.generate_all_findings` | dimension evidence pool | findings | prompt must produce implication and decision framing |

The most important mixing point is `collect_evidences()`. It accepts broad feature keys including `evidence_snippet`, `evidence_snippets`, `evidence_insights`, and persisted `evidence_items`. That is how internal visual metrics, `robots.txt`, owned claims, trust scans, and Exa results can all become ordinary dimension-level evidence.

## Deep Research Packet As Benchmark

The single-URL Deep Research trial did not prove that Deep Research should replace Brand3 acquisition. It did prove the evidence shape Brand3 is missing.

Useful categories from the packet:

- `audited_surface`
- `owned_claims`
- `external_evidence`
- `related_surface_evidence`
- `technical_signals`
- `trust_or_security_signals`
- `entity_ambiguity`
- `excluded_noise`
- `missing_evidence`
- `finding_eligible_evidence`
- `evidence_not_eligible_for_findings`
- `requires_human_review`

The key improvement was not better prose. It was source-context classification: Kit subdomain architecture, unresolved controller, BuiltWith name collision, and trust/security isolation were separated before narrative generation.

## Local Evidence Packet v0

Create a local packet from existing inputs only. It should be deterministic where possible and offline-testable from a run snapshot.

Proposed shape:

```json
{
  "version": 0,
  "case_id": "run_or_slug",
  "audit_url": "https://example.com",
  "audited_surface": {},
  "source_inventory": [],
  "owned_claims": [],
  "external_evidence": [],
  "related_surface_evidence": [],
  "technical_signals": [],
  "trust_or_security_signals": [],
  "visual_or_internal_signals": [],
  "entity_ambiguity": [],
  "excluded_noise": [],
  "missing_evidence": [],
  "finding_eligible_evidence": [],
  "evidence_not_eligible_for_findings": [],
  "requires_human_review": [],
  "dimension_evidence_inputs": {},
  "metadata": {
    "source": "existing_exa_web_pipeline",
    "llm_required": false,
    "deep_research_required": false,
    "runtime_effect": false
  }
}
```

The packet is not a new report payload. It is a pre-narrative eligibility view over information Brand3 already collected.

## Source Classification Rules

| Class | Deterministic rule | Narrative implication |
|---|---|---|
| `audited_surface` | URL host equals submitted/canonical audit host | primary surface only |
| `owned_surface` | same root/canonical domain, owned fallback URL, or explicit official URL | allowed as owned claim/source |
| `same_root_subdomain` | same registrable/root domain as audit URL | not automatically alias; can support surface structure |
| `external_third_party` | source host differs from owned domains and is not a known technical/security host | eligible only after quality/source role check |
| `search_result` | Exa result with title/text/highlights/summary | candidate evidence, not finding-ready by default |
| `technical_internal` | context, robots, sitemap, schema, crawl status, page depth, performance, raw tech stack | technical/readiness only |
| `trust_security` | security, malware, scam, blacklist, trust, sandbox, scanner domains | review-only unless source quality policy says otherwise |
| `visual_internal_metric` | visual analyzer, screenshot metrics, color/contrast/whitespace/style analysis | Visual Signature/appendix only, not market proof |
| `related_unresolved` | same-name or adjacent domain without explicit ownership relation | entity ambiguity, not alias |
| `noise` | off-topic broad market stats, unrelated same-name results, competitor material outside scope | excluded from findings |

The default posture should be conservative: if source relation is unclear, classify as unresolved or review-required rather than useful.

## Finding Eligibility Rules

| Eligibility | Meaning | Allowed downstream use |
|---|---|---|
| `eligible_for_narrative_finding` | evidence is source-qualified, URL-backed, entity-safe, and dimension-relevant | can enter findings prompt |
| `observation_only` | true but weak/owned/self-description or thin | can support observation, not strategic implication |
| `appendix_only` | useful as audit support but not narrative material | report appendix or diagnostics |
| `technical_only` | infrastructure/readiness/internal technical signal | technical diagnostic, not brand finding |
| `trust_security_review_only` | scanner/trust source needs interpretation | review section, no strategy |
| `requires_human_review` | entity relation/source quality/security meaning unresolved | block or mark before narrative |
| `reject_noise` | unrelated, duplicated, off-entity, or broad context | exclude |

Finding eligibility must be computed before the narrative prompt. The prompt should never have to decide whether `robots.txt`, local color metrics, or ambiguous same-name domains are strategic evidence.

## Entity And Surface Separation Rules

| Surface relation | Rule | Handling |
|---|---|---|
| `audited_url` | exact submitted URL or final canonical URL | primary evidence surface |
| `canonical_root` | root domain of audited URL | owned context, not necessarily same page |
| `same_root_surface` | same registrable domain/subdomain family | related; not automatically equivalent |
| `same_name_different_domain` | matching token/brand string on another root domain | unresolved unless explicit evidence links it |
| `explicit_related_surface` | discovered by official links, same organization docs, or reviewed metadata | related with evidence |
| `unresolved_surface` | plausible relation but not proven | review-required |
| `forbidden_alias_inference` | name similarity, search co-occurrence, third-party mention, or URL token match alone | must not become alias |

This rule set matters more than prose controls. It is what would have prevented BuiltWith evidence from being smoothed into a Kit subdomain audit.

## Builtwith / Kit Handling

| Problematic input | Current behavior risk | Evidence Packet v0 handling |
|---|---|---|
| Kit owned claims | repeated owned-claim findings with caveats | `owned_claims`; `observation_only` unless entity/controller is clear |
| BuiltWith.com evidence | mixed as normal positioning evidence | `related_surface_evidence` with `relationship=unresolved`; not eligible as audited-surface finding |
| `builtwith.kit.com` trust/security scans | broad perception/trust narrative | `trust_or_security_signals`; review-only unless source quality is high |
| `robots.txt` | technical site configuration finding | `technical_signals`; technical-only/appendix-only |
| visual analysis metrics | strategy about visual/UI/product intent | `visual_or_internal_signals`; never finding-eligible |
| generic technical configuration | implication/decision-space filler | `technical_only`; no strategic implication |
| evidence without URLs | allowed into findings as quote-only evidence | `missing_evidence`; not eligible unless backed by source URL or explicit internal diagnostic class |

For Builtwith/Kit, the packet's central state should be:

```text
Kit-hosted or Kit-related subdomain with unresolved specific controller,
plus a BuiltWith name collision. Do not infer ownership or affiliate relation.
```

## Downstream Simplification If Reset Works

This reset should make later controls smaller, not larger.

| Downstream piece | Current role | Expected simplification |
|---|---|---|
| Narrative Harness | detects repeated caveats, generic filler, missing URLs after generation | fewer warnings because bad evidence never enters prompt |
| EntityNarrativeState | reconstructs entity ambiguity from diagnostics | smaller; can consume explicit packet ambiguity instead of inferring from prose |
| Lab recomposition | trims bad findings after the fact | less needed; baseline findings should be cleaner |
| State-first prose generator | coordinates around contaminated evidence | can focus on composition, not evidence triage |
| Render suppression | hides generic Decision Space | should become fallback only, not primary cleanup |

Rule: a new input reset is justified only if it deletes or shrinks downstream patches.

## Smallest Safe Implementation Slice

Do not change production generation first.

Smallest slice:

1. Add one offline/local evidence packet builder.
2. Input: existing run snapshot only.
3. Output: `EvidencePacketV0` JSON artifact.
4. First fixture: Builtwith run 74 or existing Builtwith example snapshot.
5. Compare local packet against `examples/reports/deep_research_trial/builtwith_kit_com_single_url/evidence_packet.json`.
6. Do not feed packet into prompts yet.
7. Do not alter scoring, rendering, persisted payloads, collectors, or Visual Signature.

Likely module:

```text
src/reports/evidence_packet.py
tests/test_evidence_packet.py
examples/reports/evidence_packet/builtwith_kit_com.local_evidence_packet.v0.json
docs/brand3_existing_pipeline_evidence_packet_v0_review.md
```

This is still offline. Its job is to prove that existing Exa/Web/Context inputs can be ordered locally before generation.

## Future Tests And Invariants

Implementation should protect these invariants:

- Exa results do not become findings without source classification.
- Technical/internal metrics cannot become strategic implications.
- `evidence_insights` from visual/internal analysis are not finding-eligible.
- `robots.txt`, sitemap, schema, crawl status, and generic site config are technical-only.
- Owned claims remain owned claims and cannot become external validation.
- Same-name different-root domains are not aliases.
- Same-root/subdomain relation is not equivalent to ownership.
- Missing evidence URL is explicit and blocks finding eligibility by default.
- Security/trust signals are review-only unless source quality policy allows narrative use.
- Evidence eligibility is computed before narrative generation.
- Evidence packet v0 requires no LLM call.
- Deep Research is not required for local packet construction.
- Visual Signature remains separate.
- Scoring remains unchanged.

## Recommended Next Step

Implement the offline/local Evidence Packet v0 builder against existing snapshots.

Do not touch prompts until a Builtwith local packet proves it can classify:

- Kit owned claims,
- BuiltWith same-name evidence,
- technical context artifacts,
- visual/internal analysis,
- trust/security signals,
- missing URLs,
- unresolved controller ambiguity.

If it cannot do that deterministically, then Brand3 should not proceed to state-first generation changes. The input is still too disordered.

## Explicit Non-Goals

- No Tavily or new provider.
- No Deep Research runtime integration.
- No collector rewrite.
- No scoring change.
- No prompt change.
- No report generation change.
- No render change.
- No persisted payload format change.
- No Visual Signature change.
- No new Lab layer.
