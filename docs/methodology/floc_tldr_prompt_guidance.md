# FLOC* TLDR Prompt Guidance

Status: working methodology guide  
Owner: FLOC* / Brand3  
Scope: Brand3 Scanner TLDR Analyst Pass  
Last updated: 2026-06-07

## Verdict

The historical FLOC* TLDR corpus should help the Brand3 Scanner generate better
TLDRs, but only as method guidance.

It should not be used as raw client content inside product prompts. The useful
asset is not the private wording of each client TLDR. The useful asset is the
method: block structure, epistemic discipline, strategic compression and FLOC*
tone.

## Intended Use

Use this guidance to improve:

- Analyst Pass system prompts.
- TLDR block quality checks.
- golden tests and regression fixtures.
- human review rubrics.
- future anonymized few-shot examples.

Do not use it to:

- infer facts about a scanned brand from another client's TLDR.
- copy client language into prompts or generated outputs.
- train a product path on unreviewed private material.
- collapse all brands into the same FLOC* voice.

## Core Prompt Principles

### 1. TLDR Is Strategic Compression

The TLDR is not a summary of the website. It is a compact strategic artifact
created from evidence.

Prompt rule:

```text
Do not merely summarize the Research Pack. Compress the evidence into strategic
blocks that a founder, strategist, copywriter or designer could use as decision
filters.
```

### 2. Do Not Extract Literally Unless The Evidence Earns It

Some blocks may be declared directly. Others are usually performed or inferred.

Prompt rule:

```text
For each TLDR block, state whether the claim is declared, performed, inferred or
absent. Literal extraction is allowed only when the brand states the idea
clearly. Otherwise, articulate the block from traceable evidence or mark it as
not detected.
```

### 3. Magnetism Is Not A Slogan

Magnetism is the phrase, tension or emotional charge that concentrates
attention. It can be slogan-like, but it should not become invented campaign
copy.

Prompt rule:

```text
Magnetism must come from visible language, repeated tension, emotional promise
or category reframe. Do not invent a polished slogan if the evidence only
supports a weak or generic hook.
```

### 4. Brand Idea Is The Organizing Center

Brand Idea should synthesize the strategic system, not restate a feature or
tagline.

Prompt rule:

```text
Brand Idea should organize Core Purpose, Value Proposition, Personality,
Attributes, Values, Mission, Vision and Magnetism into one strategic concept.
If the evidence is sparse, return a hypothesis with lower confidence or require
human review.
```

### 5. Purpose, Mission And Vision Must Stay Separate

Common failure mode: the model turns all three into the same aspirational
sentence.

Prompt rule:

```text
Keep these separate:
- Core Purpose: why the brand exists beyond transaction.
- Mission: what the brand does or commits to doing.
- Vision: what future state the brand wants to create.
If the source material collapses them, preserve the ambiguity instead of
inventing clean distinctions.
```

### 6. Audience Is An Input Even When Not A Final Block

The current 9-block TLDR does not always expose Target Audience, but audience
still shapes Value Proposition, Mission, Brand Idea and Personality.

Prompt rule:

```text
Use audience evidence to ground the TLDR blocks. Do not add a separate audience
block unless the selected output mode requires it.
```

### 7. Evidence Gaps Are Part Of The TLDR

The strongest Brand3 output is honest about what it can and cannot know.

Prompt rule:

```text
If evidence is too thin, contradictory, generic or contaminated, lower
confidence and expose the limitation. Do not fill missing strategy with fluent
consultancy language.
```

## Recommended Analyst Pass Instruction Block

This can be adapted into the TLDR Analyst Pass prompt:

```text
You are generating a Brand3 TLDR in the FLOC* method.

Treat TLDR as strategic compression, not as a website summary.
Use the Research Pack as evidence. Do not use private examples, category
assumptions or generic consultancy language as evidence.

For every block:
- answer the block's strategic question;
- preserve claim type: declared, performed, inferred or absent;
- preserve mode: literal, compressed, interpreted_from_discourse,
  needs_human_review or not_detected;
- cite evidence refs;
- include counter-evidence or limitations when relevant;
- lower confidence when the evidence is sparse, generic or contradictory.

Do not invent Magnetism as a slogan.
Do not merge Purpose, Mission and Vision.
Make Brand Idea the organizing strategic concept, not a tagline.
Use audience evidence as grounding even when audience is not a final block.
```

## Quality Rubric

Use this rubric to evaluate generated TLDRs.

| Criterion | Good | Bad |
| --- | --- | --- |
| Strategic compression | Turns evidence into decision-ready blocks | Summarizes pages in generic prose |
| Evidence discipline | Every strong claim has evidence refs | Fluent claims without traceable support |
| Epistemic status | Declared/performed/inferred/absent are honest | Everything sounds equally certain |
| Magnetism | Captures real tension or emotional charge | Invents campaign copy |
| Brand Idea | Organizes the system | Repeats offer or tagline |
| Purpose/Mission/Vision | Distinct and bounded | Collapsed into one aspiration |
| Specificity | Uses brand-specific language and category context | Uses replaceable consultancy phrases |
| Human review | Flags sensitive/ambiguous blocks | Hides uncertainty |

## Product Integration Rule

Before this guidance influences production TLDRs, create tests that compare:

1. current Analyst Pass output;
2. Analyst Pass output with this method guidance;
3. human-reviewed judgement.

The test should ask whether the new output is:

- more specific;
- more evidence-grounded;
- less generic;
- clearer about uncertainty;
- more useful as a strategist artifact.

If it only sounds more polished, do not promote it.

## Privacy Rule

Client TLDR records may inform methodology, but their raw text should not enter
production prompts unless reviewed, redacted and approved.

Preferred safe forms:

- abstracted rules;
- anonymized examples;
- block-level anti-patterns;
- synthetic examples based on structure, not client content;
- rubric checks.

Avoid:

- raw client block text;
- client-specific strategy language;
- identifiable internal notes;
- unlabelled LLM experiments mixed with deliverables.
