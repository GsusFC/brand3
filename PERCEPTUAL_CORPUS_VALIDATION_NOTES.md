# Perceptual Corpus Validation Notes

## Scope

This note validates the pilot perceptual corpus against existing narrative harness runs without connecting the corpus to scoring.

Reviewed runs:

- `iris`
- `watermelon`
- `launchdarkly`

Validation basis:

- existing baseline vs state-first comparison artifacts in `examples/reports/narrative_harness/state_first_prose_v0/`
- current perceptual corpus hints from `src/reports/experimental_perceptual_narrative.py`
- pilot corpus case records in `examples/perceptual_library/cases/`

Interpretation of the harness comparison:

- baseline / fallback-only path: `examples/reports/narrative_harness/{run}.payload.json`
- corpus-enabled path: `examples/reports/narrative_harness/state_first_prose_v0/{run}.state_first_prose_v0.json`
- the state-first artifacts explicitly compare the baseline and corpus-assisted reading on specificity, evidence binding, entity coherence, caveat discipline, uncertainty preservation, and overreach risk

## What improved

### 1. Better separation between audited surface and adjacent or colliding surfaces

The strongest gain is on `iris`.

- Baseline reading collapses Iris-like domains into one implied story.
- The state-first candidate keeps the audited surface separate from name-collision surfaces.
- The current perceptual corpus supports that separation by surfacing explicit ambiguity and keeping ownership unresolved.
- The comparison artifacts show the corpus-assisted path winning on specificity, evidence binding, entity coherence, caveat discipline, uncertainty preservation, and overreach risk.

Practical effect:

- specificity improves
- entity coherence improves
- unsupported aliasing risk drops
- human review remains visible instead of being normalized away

### 2. Better evidence binding for owned surfaces versus ecosystem noise

The corpus is useful when the run has owned claims plus adjacent ecosystem signals.

Observed on `watermelon`:

- baseline blends owned copy, GitHub, marketplace and unrelated references into one ecosystem story
- state-first separates owned surface from unresolved adjacency
- the corpus reinforces that GitHub and marketplace signals are context, not proof of ownership or adoption
- the comparison artifacts again favor the corpus-assisted reading on specificity, evidence binding, entity coherence, caveat discipline, and overreach risk

Practical effect:

- evidence families stay distinct
- strategic reading becomes safer
- false brand-architecture claims are less likely

### 3. Better restraint on already-stable brand surfaces

Observed on `launchdarkly`:

- the run is already entity-stable
- the improvement is smaller than `iris` or `watermelon`
- the corpus adds useful caution around owned claims, but the lift is incremental rather than transformative
- the comparison artifacts show a smaller but still positive shift: corpus-assisted reading wins on evidence binding, caveat discipline, and overreach risk, while specificity improves only modestly

Practical effect:

- the output stays specific
- the warning level stays proportional
- the corpus does not force ambiguity where none is needed

## What became noisier

### 1. Internal-method language can overtake product-surface language

The pilot corpus is skewed toward internal Brand3 method artifacts:

- `rosalind_brand3_landing`
- `nektar_summary_brand_platform`
- `esco_token_brand_platform_v3`

That makes the corpus strong as a method-reading corpus, but weaker as a general product-reputation corpus.

Noise pattern:

- some wording leans toward process lineage, route structure, and method evolution
- that is useful for lab validation
- it becomes noisy if the same language is used to describe external-facing product surfaces

### 2. Caveat language can repeat if the corpus is over-applied

The pilot is good at keeping uncertainty visible, but it can become repetitive if every surface is treated as low-confidence by default.

The right balance is:

- preserve uncertainty where evidence is unresolved
- avoid turning every owned claim into a disclaimer

## Useful corpus patterns

These are the patterns worth keeping.

### `iris`

- explicit separation of audited surface versus name-collision surfaces
- evidence boundary language that does not imply shared ownership
- human review preserved for unresolved relation questions

### `watermelon`

- separation of owned promise versus ecosystem adjacency
- GitHub and marketplace treated as contextual signals, not proof of adoption
- entity ambiguity kept visible

### `launchdarkly`

- restraint around owned reliability and scale claims
- less over-caveating than the baseline
- no invented ambiguity

### Pilot corpus records

- `rosalind_brand3_landing`: good example of compressed method structure and clear review gating
- `nektar_summary_brand_platform`: good example of canonical summary versus workshop lineage separation
- `esco_token_brand_platform_v3`: good example of method evolution, but it is the most internal/process-heavy record in the pilot

## Records that need revision

No pilot record is invalid, but the corpus should be tightened before expansion.

Recommended revisions:

1. `esco_token_brand_platform_v3`
   - add a clearer distinction between method evidence and product-surface evidence
   - reduce the risk that it is read as a finished external artifact

2. `nektar_summary_brand_platform`
   - preserve the summary/workshop split, but make the source hierarchy more explicit
   - keep lineage visible without over-weighting workshop artifacts

3. `rosalind_brand3_landing`
   - keep the block-structured TLDR evidence
   - add more explicit notes on approval state and user-facing scope so it does not read as broader product validation than it is

## Recommendation

**Refine the schema before expanding the corpus.**

The pilot validates the shape of the corpus and the usefulness of the perceptual hints, but the corpus is currently skewed toward internal Brand3 method artifacts.

The current evidence supports keeping the pilot because it improves the experimental narrative output in the places that matter most for audit safety:

- it reduces false aliasing
- it improves evidence binding
- it preserves uncertainty where ownership or relation is unresolved
- it triggers human review correctly for ambiguous cases

Next step should be:

- keep the current pilot
- tighten source-role distinctions in the schema or record guidance
- add more externally anchored, user-facing examples before expansion

That is the safer path than expanding the corpus immediately.
