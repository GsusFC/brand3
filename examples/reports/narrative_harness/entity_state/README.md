# EntityNarrativeState Fixtures

This directory contains experimental offline fixtures for future Brand3 entity-level narrative composition.

These files are not runtime configuration.

They are not:

- scoring inputs,
- prompt inputs,
- report renderer inputs,
- persisted `report_narrative` payloads,
- Visual Signature artifacts,
- production gates.

## Current Fixture

```text
builtwith_kit_com.entity_narrative_state.json
```

This fixture is manually derived from:

- `examples/reports/narrative_harness/builtwith_kit_com.payload.json`
- `examples/reports/narrative_harness/builtwith_kit_com.diagnostic.json`
- `examples/reports/narrative_harness/builtwith_kit_com.render_aware.diagnostic.json`
- `docs/brand3_entity_narrative_state_design_memo.md`
- `docs/brand3_observation_repetition_family_findings.md`
- `docs/brand3_render_aware_harness_multi_report_findings.md`

## How To Read It

Read it as a composition-state sketch:

- what the entity appears to be,
- where aliases/entity ambiguity appear,
- how dense owned claims are,
- which repetition budgets were exceeded,
- where evidence URL coverage is weak,
- which contradictions may need review,
- which findings might later be compressed or demoted.

Do not read it as final analysis prose.

The fixture intentionally marks uncertain areas. It should not infer brand intent, market position, audience psychology, or strategy beyond available evidence.

## Intended Next Use

The next step, if needed, is another memo or offline fixture review. A builder function should not be added until more real persisted report narratives exist and the field shape has been tested across several cases.
