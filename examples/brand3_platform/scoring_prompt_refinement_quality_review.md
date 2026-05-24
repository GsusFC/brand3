# Scoring Prompt Refinement Quality Review

Scope:

- `examples/brand3_platform/scoring_prompt_refinement_implementation_note.md`
- `examples/brand3_platform/brand3_report_voice_guide.md`
- current report snapshots and renderer output where practical

This is an audit only. No prompts, scoring logic, renderer structure, or Visual Signature code were changed.

## Verdict

The low-risk wording pass improved the report voice in the places it could reach:

- the narrative prompts now ask for observation-first structure
- fallback prose is more specific and less boilerplate
- findings are more diagnostic and less praise-shaped
- tension handling is clearer and more evidence-led

The improvement is real, but partial. The remaining score-led language is not only a prompt problem. Some of it is structural in the report renderer and in the inherited summary layers that still emit score-first framing.

## What Improved

### 1. Reduced score-first openings

The synthesis prompt no longer asks for a score-led opening. It now explicitly asks for:

- a concrete evidence anchor
- a diagnostic first sentence
- observation -> implication -> tension ordering

The fallback synthesis also stopped opening with a literal global score line.

### 2. Fewer generic phrases

The findings prompt now rejects vague praise more aggressively and pushes the model toward:

- mismatch
- concentration
- repetition
- absence
- channel divergence

The tension prompt got the same treatment.

### 3. Better evidence anchoring

The new guidance is materially better at forcing the model to cite concrete evidence surfaces before interpreting them.

This is the strongest improvement in the patch. It should reduce abstract prose and make the report easier to verify against the source pool.

### 4. More diagnostic findings

The findings prompt is now much closer to a real editorial brief:

- observation is separated from implication
- typical decisions are framed as a decision space, not a prescription
- contradictions are treated as first-class findings

### 5. Less literary / consultant tone

The prompt language is less flowery and more operational.

The fallback prose also reads more like a diagnostic note than a generic placeholder.

## Before / After Excerpts

### Excerpt 1: synthesis opening

Before:

> `Write a SYNTHESIS PARAGRAPH about the brand ...`
> `Rules: ... DO NOT cite numbers except the global score if it helps.`

After:

> `Open with one concrete evidence anchor ... Do not open with the score.`
> `Use the observation / implication / tension order ...`

Assessment:

The opening is now guided toward evidence and structure, not score-led recap.

### Excerpt 2: synthesis fallback

Before:

> `Strongest dimension: Presence (82/100).`
> `Weakest dimension: Differentiation (54/100).`
> `Analysis data quality: degraded.`

After:

> `Cross-dimension snapshot for {brand}.`
> `Observed pattern: the clearest read sits in {top.display_name} ...`

Assessment:

This is better, but not fully score-free. It still foregrounds strongest / weakest dimension language, so it is less generic but still somewhat score-structured.

### Excerpt 3: findings structure

Before:

> `prose: 2-3 lines in English ... Mention at least one concrete detail.`

After:

> `observation / implication / tension`
> `Start with one concrete quote, page, source domain, or channel ...`

Assessment:

This is a clear improvement. It should produce more reusable perceptual knowledge and less one-off summary text.

### Excerpt 4: tensions

Before:

> `Decide whether ONE significant cross-dimensional tension exists.`
> `If no meaningful tension exists, return null.`

After:

> `Identify ONE significant cross-dimensional TENSION if and only if one genuinely exists ...`
> `Keep the language specific to the evidence pool. Avoid generic praise ...`

Assessment:

The guidance is sharper and less likely to hallucinate a tension, but it still leans on familiar consultant terms like `strategic question` and `trade-off space`.

### Excerpt 5: renderer holdout

Snapshot evidence still contains:

> `Example scores 72/100 (band B). Strongest dimension: Presence (82/100). Weakest dimension: Differentiation (54/100).`

Assessment:

This is outside the low-risk prompt patch. It confirms that score-first voice is partly structural and will not disappear until the renderer summary layers are revised.

## Remaining Issues

1. The synthesis fallback still uses strongest / weakest dimension language.
2. The renderer still emits score-led summary prose in the report hero / current reading area.
3. The phrase set still contains some consultant-y terms:
   - `strategic question`
   - `trade-off space`
   - `substantive read`
4. The wording may now over-bias toward evidence anchors at the expense of readability if the model becomes too literal.

## Remaining Phrases To Eliminate

- `strategic question`
- `trade-off space`
- `substantive read`
- `clear message`
- `strong presence`
- `well-defined identity`
- `the available sources point in the same direction`
- `automatic synthesis unavailable`

## Overcorrection Risk

The biggest risk is overconstraining the model into repetitive, quote-led prose.

Symptoms to watch for:

- every paragraph starting the same way
- excessive reuse of `observed pattern`
- too many `may / could / suggests` qualifiers
- awkwardly literal evidence anchoring that reads like a log line rather than a report

## Next Recommended Changes

### Low risk

- Remove the remaining strongest / weakest wording from fallback synthesis.
- Replace residual consultant phrases with plainer editorial language.
- Regenerate snapshots once the prompt output stabilizes.

### Medium risk

- Rework the renderer's score-first summary layer.
- Reduce duplicated summary prose across the current reading and the per-dimension sections.
- Add a more explicit distinction between summary metadata and the narrative paragraphs.

### Future

- Move toward a sharper Brand3 / FLOC* analytic voice that is more diagnostic than summary-like.
- Treat the report hero as metadata, not the narrative lead.
