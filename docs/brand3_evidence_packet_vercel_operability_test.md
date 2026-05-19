# Brand3 Evidence Packet v0 Vercel Operability Test

## Purpose

Test whether local Evidence Packet v0 works on a high-evidence, stable entity case without over-filtering useful evidence.

- Target: `https://vercel.com/`
- Run: `79`
- Mode: lab/offline packet test after one local Brand3 audit snapshot
- Packet: `examples/reports/evidence_packet/vercel.local_evidence_packet.v0.json`

## Result

Evidence Packet v0 is useful as a diagnostic filter, but it is not yet operational as a replacement for finding input preparation.

It does preserve meaningful evidence for Vercel, which is important: the classifier is not simply blocking everything. But it also lets through URL-only evidence with no quote/text, loses differentiation coverage, and treats too many external source roles with the same coarse logic.

## Snapshot Baseline

| Item | Value |
| --- | --- |
| Composite | 75.9 |
| Current narrative evidence count | 26 |
| Packet eligible evidence | 13 |
| Packet blocked/not eligible | 17 |
| Missing evidence URL items | 9 |
| Requires human review | 1 |

## Dimension Comparison

| Dimension | Current prompt evidence | Packet eligible | Packet blocked |
| --- | ---: | ---: | ---: |
| coherencia | 5 | 1 | 6 |
| presencia | 7 | 3 | 8 |
| percepcion | 3 | 3 | 0 |
| diferenciacion | 4 | 0 | 3 |
| vitalidad | 7 | 6 | 0 |

## What Worked

- Stable entity behavior is better than Builtwith/Kit: Vercel keeps 13 eligible items instead of being globally blocked.
- Technical/context artifacts are not treated as strategy: `robots.txt`, `sitemap.xml`, `llms.txt`, schema, key-page presence, and visual metrics are classified as technical/internal.
- Owned and external evidence are at least separated structurally.
- Same-name external profiles are review-gated instead of treated as aliases.

## What Failed Operationally

- Differentiation has zero eligible packet evidence, even though the current audit has differentiation inputs. That means packet-filtered generation would underwrite the dimension.
- 3 eligible items have a URL but no evidence text. This is not prompt-safe; a URL alone is not a finding anchor.
- External source roles are too coarse. Wikipedia, TechCrunch, Releasebot, togithub mirrors, and owned Vercel pages need different eligibility semantics.
- Social verification is too blunt. LinkedIn is safely review-gated, but stable entities need official-link verification rather than generic same-name caution.

## Evaluation

| Question | Answer |
| --- | --- |
| Preserve strong owned evidence? | Partially |
| Preserve strong external evidence? | Partially |
| Avoid docs/technical artifacts as strategy? | Yes |
| Avoid blocking too much? | Mixed |
| Create cleaner prompt input? | Partially, not ready |
| Replace current evidence preparation? | No |

## Root Cause

The packet is doing the right kind of work, but the eligibility contract is still too shallow. It classifies source families, but it does not yet enforce enough evidence-text quality, source-role weighting, official-link verification, or dimension coverage.

## Recommended Next Step

Do one narrow hardening pass before any prompt integration:

1. Block empty-text URL evidence from normal finding eligibility.
2. Add source-role subtypes: `owned_page`, `owned_changelog`, `news_article`, `encyclopedic_profile`, `release_aggregator`, `code_mirror`, `official_social_candidate`, `comparison_page`.
3. Verify social/profile candidates against owned links or raw input metadata.
4. Add dimension coverage checks so packet-filtered generation can abstain per dimension.
5. Re-run Vercel, LaunchDarkly, Watermelon, and Builtwith without touching prompts.

## Decision

Do not feed Evidence Packet v0 into generation yet. It is operational enough to expose input-order problems cheaply, but not operational enough to become the finding prompt contract.
