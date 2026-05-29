# TLDR Brand3 Research Pack -> Analyst Pass Decision

Date: 2026-05-28

## Verdict

Hay un mejor enfoque disponible: resetear el TLDR Brand3 hacia un flujo
Research Pack -> Analyst Pass y no seguir convirtiendo fallos observados por
marca en reglas de producto.

## Decision

The next TLDR Brand3 implementation should separate acquisition, evidence
classification, and strategic interpretation:

1. Research Pack: normalize the available Brand Audit evidence, entity scope,
   surface role, source role, proof points, page chrome, content/article noise,
   and block-relevant evidence candidates.
2. Analyst Pass: answer each TLDR block from the Research Pack using the Brand3
   analyst questions, claim types, confidence, limitations, and review flags.
3. Benchmark: use existing runs such as Base44, Bokeroon, Fly, Every, and
   tinyNature to evaluate the flow.

## Rejected Approach

Do not add Base44/Bokeroon-specific keyword lists, one-off regex cleanup, or
fixture-driven assertions directly to the main block interpreters as the primary
architecture. Those patches can hide the current failure mode: the scanner often
has useful evidence but lacks the right research packet and analyst reasoning
step to choose and synthesize it.

## What Stays

- `docs/tldr_brand3_existing_runs_benchmark.md` stays as benchmark and learning
  material.
- Existing Brand3 Lab and Reverse Engineering deprecation work remains a
  separate cleanup track.
- Current TLDR interpreter code remains the base until the Research Pack ->
  Analyst Pass implementation replaces or wraps it.

## Current Working Tree Classification

- Benchmark/documentation: `docs/tldr_brand3_existing_runs_benchmark.md` and
  this decision note.
- Deprecation cleanup: Brand3 Lab, Reverse Engineering, perceptual library, and
  narrative shadow adapter deletions plus related web/test/report references.
- Product logic retained from prior cleanup: removal of Brand3 Lab links/routes
  and fallback handling for removed perceptual artifacts.
- Tactical TLDR patches discarded from this reset: Base44/Bokeroon keyword
  additions, page-chrome regex cleanup, brand-specific benchmark tests in
  `tests/test_magnetism_tldr_rules.py`, and the lab-subdomain entity heuristic
  in `src/discovery/entity_discovery.py`.
- Non-product context churn: `AGENTS.md` memory-context refresh.

## Next Implementation Boundary

The next code change should introduce the Research Pack contract or Analyst Pass
contract first. Tactical extraction fixes are acceptable only when they serve
that contract and are tested as general evidence classification behavior, not as
brand-specific output patches.
