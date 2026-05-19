# Deep Research Reference vs Local Evidence Packet v0

## Purpose

This memo compares the useful Watermelon Deep Research evidence-packet reference against the current local Evidence Packet v0 builder.

The goal is practical:

what can Brand3 produce cheaply with its existing Exa/Web/snapshot data, and what should remain a manual or expensive escalation?

## Inputs Compared

Deep Research reference:

- target: `https://watermelon.sh`
- single URL;
- Google Search and URL context;
- structured evidence packet produced in a manual run;
- no previous Brand3 evidence;
- no seed URLs.

Local Evidence Packet v0:

- artifact: `examples/reports/evidence_packet/builtwith_kit_com.local_evidence_packet.v0.json`
- input: existing Brand3 snapshot only;
- no network;
- no Exa/API calls;
- no LLM;
- no Deep Research.

These are not identical cases, so the comparison is about contract capability, not case outcome.

## Capability Comparison

| Capability | Deep Research reference | Local Evidence Packet v0 | Practical conclusion |
|---|---|---|---|
| Start from one URL | yes | only if snapshot already exists | local builder is post-collection, not acquisition |
| Discover related surfaces | strong | weak; only classifies collected data | needs upstream Exa/Web enrichment |
| Entity resolution | strong but may overstate confidence | conservative but limited | combine deterministic rules with explicit discovered sources |
| Source inventory | strong | partial | local v0 should add clearer source inventory by URL/source role |
| Owned vs external separation | strong | strong for existing items | local v0 can do this cheaply |
| Related-surface classification | strong | medium | local v0 needs explicit relation types and evidence links |
| Same-name noise exclusion | strong | medium | local v0 can improve with same-name/domain rules |
| Technical-only handling | strong | strong | keep local deterministic rule |
| Trust/security gating | good | strong | keep local deterministic review gate |
| Marketplace/listing handling | nuanced but sometimes too permissive | limited | local v0 should classify marketplace as observation/review-gated by default |
| Missing evidence | strong | strong | keep as first-class output |
| Finding eligibility | useful but still sometimes permissive | very conservative | local v0 should stay conservative |
| Contradiction candidates | useful | limited | add candidate bucket when facts conflict without resolving them |
| Cost | high | near-zero runtime cost | Deep Research cannot be default |
| Output control | depends on prompt/schema | deterministic | local v0 is safer for default pipeline |

## What Local v0 Already Gets Right

The local builder already has the most important safety behaviors:

- it does not treat technical artifacts as strategic evidence;
- it keeps visual/internal metrics out of findings;
- it marks URL-less evidence as missing evidence;
- it marks same-name different-root surfaces as unresolved;
- it gates trust/security sources;
- it does not call the network or an LLM;
- it has a stable output shape.

This is enough to stop the worst current Brand3 failure:

mixed evidence becoming strategic prose.

## What Deep Research Does Better

Deep Research is better at acquisition and discovery:

- finds related surfaces not already in the snapshot;
- finds explicit linking relationships;
- finds directory and marketplace listings;
- finds third-party category language;
- identifies same-name unrelated entities;
- exposes source quality differences;
- can surface contradiction candidates such as inconsistent counts or emails.

The most valuable part is not prose. It is source-context discovery.

## What Deep Research Does Worse

Deep Research is not reliably disciplined unless the output contract is strict.

The failed local Watermelon prism trial showed:

- high cost;
- narrative audit output instead of JSON;
- premature interpretation;
- positive/strategic language before eligibility was settled;
- weak output controllability.

Even the better reference output still needs review because:

- confidence can be too high;
- marketplace evidence can be too easily promoted;
- repository activity can be overread as vitality;
- owned claims can still feel more validated than they are.

## What Brand3 Should Build Cheaply

Brand3 should extend local Evidence Packet v0 toward the reference shape:

1. `entity_resolution`
   - primary entity;
   - confidence;
   - explicit related surfaces;
   - relation type;
   - relationship status;
   - evidence;
   - review gate.

2. `source_inventory`
   - every source URL;
   - source type;
   - source quality;
   - role;
   - notes.

3. Dimension buckets
   - `owned_claims`;
   - `external_evidence`;
   - `related_surface_evidence`;
   - `technical_signals`;
   - `trust_or_security_signals`;
   - `finding_eligible_evidence`;
   - `evidence_not_eligible_for_findings`;
   - `missing_evidence`;
   - `requires_human_review`.

4. Cross-dimension evidence
   - owned claims;
   - external validation;
   - technical-only;
   - trust/security;
   - excluded noise;
   - entity ambiguity;
   - contradiction candidates.

5. Conservative finding eligibility
   - owned claims are eligible only as owned claims;
   - marketplace listings are observation-only unless independently verified;
   - GitHub/repository evidence supports developer activity, not adoption;
   - usage and install claims require independent support;
   - missing URLs block normal finding eligibility.

## What Should Remain Expensive Or Manual

Keep these outside default runtime:

- Deep Research;
- broad entity investigation;
- unresolved ownership review;
- heavy same-name disambiguation;
- source-quality judgment for unfamiliar directories;
- manual validation of usage/install claims;
- deciding whether a repository/org relation is official when no explicit link exists.

These are escalation tasks, not default audit tasks.

## Implication For Current Brand3

The current generation problem begins before generation.

If Brand3 feeds the model mixed inputs, no downstream narrative layer will fully recover.

The right next move is not another prose generator. It is a better pre-narrative evidence order:

collection -> evidence packet -> eligibility -> generation

The local builder is the right default mechanism. Deep Research is the benchmark and escalation path.

## Recommended Next Step

Implement the next local Evidence Packet v0 hardening slice:

- add `source_inventory`;
- add explicit `entity_resolution.related_surfaces`;
- add relation types and relationship statuses;
- add contradiction candidates;
- make marketplace/repository eligibility more conservative;
- run it on Watermelon and LaunchDarkly snapshots if available.

Do not feed it into generation yet.

Do not run more Deep Research until the local packet shape has caught up enough to compare cleanly.

## Non-Goals

- No runtime integration.
- No prompt rollout.
- No scoring changes.
- No report generation changes.
- No rendering changes.
- No Visual Signature changes.
- No Deep Research automation.
- No new provider.

