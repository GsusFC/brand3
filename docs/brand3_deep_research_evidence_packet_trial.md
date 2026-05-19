# Brand3 Deep Research Evidence Packet Trial

## Purpose

This trial tested whether Gemini Deep Research can produce a cleaner evidence packet than the current Brand3 acquisition and evidence-mixing pipeline while keeping scope and cost controlled.

Target: `builtwith.kit.com`

Mode:

- one interaction only
- Deep Research standard, not Max
- `url_context` tool only
- no open Google Search
- no scoring
- no findings
- no strategy
- no report writing

## Artifacts

- `examples/reports/deep_research_trial/builtwith_kit_com/request.json`
- `examples/reports/deep_research_trial/builtwith_kit_com/raw_interaction.json`
- `examples/reports/deep_research_trial/builtwith_kit_com/evidence_packet.json`
- `examples/reports/deep_research_trial/builtwith_kit_com/cost_observation.json`
- `examples/reports/deep_research_trial/builtwith_kit_com/trial_notes.md`
- `scripts/deep_research_evidence_packet_trial.py`

## Execution Summary

The interaction completed and returned a parseable evidence packet.

Observed usage:

- total input tokens: `65,000`
- total output tokens: `9,385`
- total thought tokens: `26,347`
- total tokens: `100,732`
- open Google Search: disabled
- tool-use tokens reported: `0`

Approximate cost estimate using Gemini 3.1 Pro Preview standard rates and counting thought tokens as output: `USD 0.558784`.

This is observable, but not cheap for a URL-only evidence packet. It is cheaper than a broad multi-agent workflow might be, but too expensive to use casually for every audit without a strict trigger.

## Evidence Packet Quality

### What improved versus the current Brand3 pipeline

Deep Research produced a cleaner semantic split than the current feature-to-evidence path:

- separated `audited_surface`
- separated `owned_claims`
- separated `external_evidence`
- separated `related_surface_evidence`
- separated `technical_signals`
- separated `trust_or_security_signals`
- explicitly named `entity_ambiguity`
- created `evidence_not_eligible_for_findings`
- marked `requires_human_review`

The strongest result is that it did **not** smooth the Kit/BuiltWith ambiguity into normal positioning. It explicitly treated the subdomain `builtwith.kit.com` as ambiguous relative to `kit.com` and `builtwith.com`.

It also correctly classified technical infrastructure such as iframes, SSL, Cloudflare, Tranco rank, and speed as not eligible for narrative findings.

### What was weaker than expected

The packet says direct inspection data from `https://builtwith.kit.com` was unavailable and relies heavily on ScamAdviser for the audited surface. That is a problem. The result is cleaner than the current Brand3 evidence mixing, but the evidence basis is thinner than expected for a URL-context-only run.

It also did not provide useful content from the Joe Sandbox URL, and it treated the fixed URL as missing evidence.

This means Deep Research did better at classification discipline than direct acquisition completeness.

## Comparison Against Current Pipeline

| Area | Current Brand3 pipeline | Deep Research trial |
|---|---|---|
| Evidence cleanliness | Mixed; feature raw values double as evidence containers | Cleaner; explicit evidence classes |
| Entity separation | Weak; Kit and BuiltWith evidence can mix by dimension | Better; entity ambiguity named directly |
| Owned vs external | Coarse source type only; owned claims still become strategic findings | Better; owned claims separated and uncertainty marked |
| Technical signal handling | Weak; `robots.txt` and visual metrics can become findings | Better; technical signals marked not eligible |
| Trust/security handling | Can become broad perception findings | Better separated, though still reliant on ScamAdviser |
| Evidence URL coverage | Mixed; URL-less evidence can enter findings | Stronger citation requirement, but direct URL coverage incomplete |
| Excluded noise | No explicit exclusion class | Explicit excluded noise |
| Cost observability | Existing pipeline cost split across collectors/LLM calls | Interaction usage was observable |
| Cost level | Already paid through current collectors and LLM calls | About USD 0.56 for one URL-only run |

## Cost Assessment

The trial was cost-observable, but the token count is high for the value returned.

Deep Research should not replace the full acquisition pipeline by default. It is more plausible as:

- a fallback for entity ambiguity
- a manual evidence-cleaning tool
- a high-friction research mode for cases where Brand3 detects mixed entity/source risk
- a benchmark against the current pipeline

It should not run on every audit.

## Can It Replace Current Acquisition?

Not directly.

It could reduce parts of the current pipeline only if:

1. direct audited-surface reading is reliable,
2. usage remains observable,
3. output stays structured,
4. a strict trigger decides when to use it,
5. Brand3 still keeps deterministic technical/scoring collectors separate.

For now, Deep Research looks more useful as an **evidence classification and entity ambiguity audit tool** than as a full acquisition replacement.

## Root Finding

Deep Research handled the exact failure class that hurt Builtwith better than the current pipeline: it separated technical signals, owned claims, related surfaces, and entity ambiguity before narrative generation.

But it also showed a new risk: a clean classification can still be built on incomplete direct access. The packet is cleaner, but not automatically more complete.

## Recommended Next Step

Do not integrate Deep Research into runtime yet.

Next controlled step:

**Specify a Deep Research Evidence Packet Contract and compare it with a deterministic Brand3 Information-to-Evidence Contract.**

The decision should be:

- deterministic local eligibility gate for normal audits,
- Deep Research only as an optional ambiguity/escalation path.

## Non-Goals Preserved

- No production collector changes.
- No scoring changes.
- No prompt rollout.
- No report generation changes.
- No rendering changes.
- No persisted payload format changes.
- No Visual Signature changes.
- No runtime integration.
- No open Google Search.
- No repeated retries.

