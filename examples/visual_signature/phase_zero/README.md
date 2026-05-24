# Visual Signature Phase Zero

Phase Zero is the contract layer for Brand3 perceptual infrastructure.
It defines a small initial taxonomy, machine-validatable schemas, fixture
records, eligibility rules, and a local validation workflow.

It is not:

- a scoring system
- a model-training pipeline
- a taxonomy playground
- a place to add product concepts without a test or validation need

## Folder tree

```text
phase_zero/
  README.md
  taxonomy/
    observation_registry.json
    state_registry.json
    transition_registry.json
    scoring_registry.json
    uncertainty_policy.json
  schemas/
    observation_registry.schema.json
    state_registry.schema.json
    transition_registry.schema.json
    scoring_registry.schema.json
    uncertainty_policy.schema.json
    uncertainty_profile.schema.json
    reasoning_trace.schema.json
    perceptual_observation.schema.json
    perceptual_state.schema.json
    transition_record.schema.json
    mutation_audit.schema.json
    dataset_eligibility.schema.json
  fixtures/
    observation_record.example.json
    state_record.example.json
    transition_record.example.json
    mutation_audit.example.json
    reasoning_trace.example.json
    uncertainty_profile.example.json
    dataset_eligibility.example.json
  manifests/
    phase_zero_manifest.json
```

## Local workflow

Generate the checked-in artifacts:

```bash
./.venv/bin/python scripts/visual_signature_phase_zero_generate.py
```

Validate the generated files:

```bash
./.venv/bin/python scripts/visual_signature_phase_zero_validate.py
```

The validation script checks:

- registry JSON shape
- registry keys are known and small
- schema JSON presence and constrained `schema_version`
- append-only records include `taxonomy_version`
- fixture model validity
- dataset eligibility example validity

## How to add a new observation safely

1. Add the observation to `src/visual_signature/phase_zero/catalog.py`.
2. Keep the key short, stable, and semantically narrow.
3. Decide whether the observation belongs to the `functional` or
   `editorial` layer.
4. Add or update a fixture record that uses the new observation.
5. Regenerate artifacts:

   ```bash
   ./.venv/bin/python scripts/visual_signature_phase_zero_generate.py
   ```

6. Validate artifacts:

   ```bash
   ./.venv/bin/python scripts/visual_signature_phase_zero_validate.py
   ```

Do not add a new observation unless a test or validation rule requires it.

## How eligibility works

A record is exportable only when:

- raw evidence is preserved
- the schema is valid
- mutation lineage is preserved if a mutation exists
- unsupported inference is absent or explicitly labeled
- required review has completed
- confidence meets the threshold or uncertainty is explicitly accounted for

The executable eligibility rule lives in
`src/visual_signature/phase_zero/eligibility.py`.

## Boundary

This folder is evidence infrastructure only. It does not affect scoring,
rubric dimensions, production reports, or production UI.
