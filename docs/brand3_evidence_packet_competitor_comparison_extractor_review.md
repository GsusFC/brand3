# Brand3 Evidence Packet Competitor Comparison Extractor Review

Date: 2026-05-18  
Scope: offline/lab only. No prompt, score, renderer, report-generation, collector, provider, or Visual Signature changes.

## What Changed

Evidence Packet v0 now extracts a narrow `competitor_comparison` evidence type from existing snapshot features where:

- `dimension_name=diferenciacion`
- `source=competitor_web_comparison`

The extractor emits bounded evidence for:

- closest measured competitor
- most different measured competitor
- average distance
- number of competitors analyzed

When no public URL exists for the comparison record, provenance is explicit and internal: `snapshot://feature/competitor_web_comparison`.

## Status Matrix

| Case | coherencia | presencia | percepcion | diferenciacion | vitalidad | comparison items |
| --- | --- | --- | --- | --- | --- | --- |
| Linear | ready | thin | ready | ready | ready | 2 |
| Builtwith/Kit | blocked | blocked | blocked | blocked | blocked | 2 |
| Watermelon | ready | thin | thin | blocked | blocked | 2 |
| LaunchDarkly | review_required | thin | thin | ready | ready | 2 |
| Vercel | thin | thin | ready | ready | ready | 2 |

## Linear Result

Linear moved from `diferenciacion=abstain` to `diferenciacion=ready`.

That change came only from existing `competitor_web_comparison` snapshot data. No new audit, provider, search, LLM call, or prompt change was used.

The generated evidence is intentionally narrow. Example shape:

- closest measured competitor with measured distance
- most different measured competitor with measured distance
- average distance
- competitors analyzed

It does not claim superiority, product quality, adoption, customer choice, durable defensibility, or planning direction.

## Conservative Behavior

Builtwith/Kit remains blocked because unresolved entity ambiguity blocks competitor comparison readiness.

Watermelon remains blocked for `diferenciacion` for the same reason: local comparison evidence cannot override unresolved entity/surface ambiguity.

LaunchDarkly and Vercel become ready on `diferenciacion` because their snapshots contain competitor comparison evidence and do not hit the material entity-ambiguity block.

## Assessment

This is enough to test a prompt-input candidate next.

The important shift is that Evidence Packet v0 can now express: “this dimension is ready because there is bounded comparison evidence” instead of forcing the LLM to infer differentiation from owned claims or generic external mentions.

Remaining work before runtime use:

- attach better provenance to competitor comparison sources
- expose competitor corpus metadata explicitly
- keep entity-resolution gates before comparison evidence is trusted
- test prompt input using only ready dimensions before generating prose

## Non-goals Preserved

No runtime integration, prompt changes, scoring changes, report-generation changes, rendering changes, Visual Signature changes, Deep Research calls, Exa/Firecrawl calls, or new provider was added.
