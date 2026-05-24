# Brand3 Single-URL Deep Research Evidence Packet Trial

## Purpose

This trial tested the realistic replacement question:

Can Gemini Deep Research start from one audit URL and produce a cleaner, better-classified evidence packet than Brand3's current acquisition and evidence-mixing pipeline?

Target URL: `https://builtwith.kit.com`

This was not a report-generation trial. Deep Research was asked only to acquire and classify evidence.

## Scope

Mode:

- one interaction only
- single audit URL only
- no seed URLs
- no previous Brand3 evidence
- Google Search allowed
- URL context allowed for the target URL
- no Deep Research Max
- no findings
- no scoring
- no recommendations
- no report prose

Artifacts:

- `examples/reports/deep_research_trial/builtwith_kit_com_single_url/request.json`
- `examples/reports/deep_research_trial/builtwith_kit_com_single_url/raw_interaction.json`
- `examples/reports/deep_research_trial/builtwith_kit_com_single_url/evidence_packet.json`
- `examples/reports/deep_research_trial/builtwith_kit_com_single_url/cost_observation.json`
- `examples/reports/deep_research_trial/builtwith_kit_com_single_url/trial_notes.md`

## Execution Summary

The interaction completed and returned a parseable evidence packet.

Observed usage:

- total input tokens: `324,313`
- total output tokens: `21,653`
- total thought tokens: `31,214`
- total tool-use tokens: `113,391`
- total tokens: `490,571`
- cached tokens: `129,024`
- Google Search: enabled through the default Deep Research tools
- seed URLs: not provided
- previous Brand3 evidence: not provided

Estimated cost:

- approximate model cost: `USD 2.248858`
- basis: Gemini 3.1 Pro Preview standard long-context rates, counting thought tokens as output
- Google Search charge: excluded from estimate; pricing depends on free monthly allowance and billable search count visibility

This was materially more expensive than the URL-context-only seeded trial, which estimated about `USD 0.558784`.

## What Search Changed

The single-URL Search trial discovered evidence that the seeded URL-context trial did not provide directly:

- Kit documentation explaining `.kit.com` domains and account/custom domain behavior.
- BusinessWire and domain-industry sources describing ConvertKit's rebrand to Kit.
- A ConvertKit email tracking redirect URL that showed `utm_campaign=poweredby`, `utm_content=email`, `utm_medium=referral`, and `utm_source=dynamic`.
- ANY.RUN and blacklist/security sources beyond the original Joe Sandbox / ScamAdviser pair.
- A clearer explanation that `builtwith.kit.com` may be a Kit-hosted subdomain or tracking endpoint, while specific controller ownership remains unresolved.

The most useful evidence was not broad brand information. It was source-context evidence about Kit's subdomain system.

## Evidence Packet Quality

### Improvements

The single-URL packet did a better job than the current Brand3 pipeline at:

- separating the audited surface from `kit.com`, `builtwith.com`, and ConvertKit-related surfaces
- avoiding a false alias between `builtwith.kit.com` and `builtwith.com`
- identifying Kit's `.kit.com` subdomain model as central evidence
- marking BuiltWith.com as unresolved rather than related by default
- treating security scans as trust/security signals, not positioning
- excluding broad BuiltWith market statistics from findings
- marking exact ownership/control as unresolved
- requiring human review for security-scan interpretation

### Weaknesses

The packet also showed serious limits:

- It inferred "Kit Platform Subdomain / Tracking Endpoint" with only medium confidence.
- It did not prove who controls the specific `builtwith.kit.com` subdomain.
- It introduced ANY.RUN security data, which may be useful but also raises triage burden.
- It still used long-context agent behavior for a narrow task, producing a high token bill.
- The output is cleaner than Brand3's current evidence mixing, but not cheap enough for default audit use.

## Comparison

| Area | Current Brand3 pipeline | URL-context-only Deep Research | Single-URL Search Deep Research |
|---|---|---|---|
| Starting input | Brand3 collectors and feature raw values | Fixed seed URL set | One audit URL |
| Discovery | Broad but internally mixed | No real discovery beyond seeds | Stronger discovery from Search |
| Entity separation | Weak; Kit and BuiltWith can mix by dimension | Better, but seeded | Strongest; explicitly avoids false alias |
| Owned vs external | Coarse source type only | Better classification | Better classification plus discovered source roles |
| Technical signals | Can become findings | Marked not eligible | Marked not eligible, but with more security detail |
| Related surfaces | Can be mixed into dimensions | Separated if provided | Discovered and separated |
| Evidence URL coverage | Mixed; URL-less findings possible | Better citation discipline | Better citation discipline |
| Noise exclusion | No explicit class | Explicit excluded noise | Better excluded noise, including broad BuiltWith stats |
| Cost | Existing distributed cost | About `USD 0.56` | About `USD 2.25` plus possible Search charges |
| Replacement readiness | Current baseline | Not replacement | Not default replacement; possible escalation path |

## Builtwith Finding Implications

If Brand3 had received this packet before finding generation, it should not have produced the original Builtwith/Kit narrative shape.

Specifically:

- `Email-first OS for creators` could remain only as a Kit-owned claim, not external validation.
- `Technology intelligence provider` should not be merged into the audited surface without explicit ownership evidence.
- `Visual analysis metrics` should not become strategy.
- Trust/security scans should be isolated as technical/security review material, not broad brand perception.
- The central narrative state should be: Kit-hosted subdomain with unresolved controller and BuiltWith name collision.

This is a better evidence contract than the current mixed feature pool.

## Cost Assessment

This trial is not viable as the default acquisition path.

The cost is the problem:

- Search improved acquisition quality.
- But the interaction crossed the 200k-token threshold and used almost 500k total tokens.
- The estimated model cost was about four times the previous URL-context-only trial.
- Search billing was not directly itemized in the interaction output.

Cost is observable enough to reject default automation, but not observable enough to make a safe product budget without additional metering.

## Replacement Assessment

Deep Research with Search could reduce or replace some of Brand3's current acquisition/mixing logic only in a lab or escalation mode.

It should not replace:

- deterministic screenshot capture
- technical collectors
- scoring feature collectors
- Visual Signature
- normal low-cost web evidence collection

It could replace or supplement:

- ambiguous entity disambiguation
- related-surface discovery
- owned-vs-external classification
- evidence eligibility triage
- "should this evidence become a finding?" review

## Root Finding

The single-URL Search trial proves that Deep Research can produce a better evidence-discipline packet from one URL than Brand3's current evidence-mixing layer.

It does not prove that Deep Research should replace the acquisition pipeline.

The value is real, but the cost and control profile are not acceptable for default runtime use.

## Recommended Next Step

Do not integrate Deep Research into runtime.

The next practical step is to design a local deterministic `Information-to-Evidence Contract` that borrows the useful output categories from the Deep Research packet:

- audited surface
- owned claims
- external evidence
- related surfaces
- technical-only signals
- trust/security signals
- entity ambiguity
- excluded noise
- finding-eligible evidence
- appendix-only evidence
- requires human review

Deep Research should remain a manual/lab escalation benchmark for hard entity-ambiguity cases until cost can be capped and output quality can be tested across more single-URL cases.

## Non-Goals Preserved

- No production collector changes.
- No scoring changes.
- No prompt rollout.
- No report generation changes.
- No rendering changes.
- No persisted payload format changes.
- No Visual Signature changes.
- No runtime integration.
- No repeated Deep Research tasks.
- No Deep Research Max.
