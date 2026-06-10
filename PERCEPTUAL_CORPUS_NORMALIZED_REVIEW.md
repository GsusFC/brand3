# PERCEPTUAL_CORPUS_NORMALIZED_REVIEW

## Executive summary

The six normalized perceptual case records are mostly consistent and useful for expansion, with one explicit exception: `meta4_english` should remain `needs_human_review` and should not be promoted into the stable narrative-hint set.

At the corpus level:

- domain normalization is working
- crypto/web3 language is being isolated in `domain_specific_noise`
- reusable pattern refs are mostly transferable and non-duplicative
- stable narrative hints should continue to use only normalized records

The corpus is **conditionally ready for expansion batch 2** if the same discipline is kept: normalized records feed stable hints, and review-only records stay out of the stable narrative path.

## Per-record review

### 1. `rosalind_brand3_landing`

**Verdict:** accepted

**Why it is strong**

- `original_domain` is set to `culture`, which matches the project-style source.
- `traditional_equivalent_category` is clear and useful: `brand strategy and landing page`.
- `business_model_analogy` is concrete: `creative services engagement`.
- `transferable_brand_patterns` are well chosen and transferable:
  - `Category-To-Surface Translation`
  - `Evidence-Bound Behavior`
  - `Block-Structured Strategic Layout`
- `domain_specific_noise` is empty, which is appropriate for a culture-based record.
- `normalization_status` is correctly `normalized`.

**Quality note**

- The source reference points to the local Brand3 TL;DR database documentation rather than a canonical remote URL, so traceability is good but slightly less direct than the later canonical-URL cases.

---

### 2. `nektar_summary_brand_platform`

**Verdict:** accepted

**Why it is strong**

- `original_domain` is correctly `culture`.
- `traditional_equivalent_category` is useful: `brand platform and design sprint summary`.
- `business_model_analogy` is clear: `design sprint workshop output`.
- `transferable_brand_patterns` are stable and non-leaky:
  - `System Cohesion Difference`
  - `Evidence-Bound Behavior`
  - `Canonical Summary Versus Lineage Separation`
- `domain_specific_noise` is empty, which is appropriate.
- `normalization_status` is `normalized`.

**Quality note**

- Like Rosalind, the source is traceable but comes through the local TL;DR database documentation instead of a direct canonical source URL.

---

### 3. `esco_token_brand_platform_v3`

**Verdict:** accepted

**Why it is strong**

- `original_domain` is correctly `web3`.
- `traditional_equivalent_category` is useful and appropriately de-cryptoed: `brand platform and method evolution document`.
- `business_model_analogy` is clear: `versioned strategy platform`.
- `transferable_brand_patterns` are good and do not depend on token-specific language:
  - `Category-To-Surface Translation`
  - `Evidence-Bound Behavior`
  - `Claim / Signal Gap`
- `domain_specific_noise` is correctly separated:
  - `token`
  - `superseded versions`
  - `live process`
  - `analysis internal`
- `normalization_status` is `normalized`.

**Quality note**

- This record is one of the better examples of stripping web3-specific words out of reusable logic while preserving the source meaning.

---

### 4. `blockdyne_master_brand3`

**Verdict:** accepted, with a mild abstraction caveat

**Why it is strong**

- `original_domain` is correctly `web3`.
- `traditional_equivalent_category` is useful: `civic infrastructure and modular systems`.
- `business_model_analogy` is understandable: `service / systems design`.
- `transferable_brand_patterns` are appropriate:
  - `Category-To-Surface Translation`
  - `Evidence-Bound Behavior`
  - `Claim / Signal Gap`
- `domain_specific_noise` is correctly isolated:
  - `sovereignty`
  - `decentralized`
  - `physical and digital infrastructure`
- `normalization_status` is `normalized`.

**Quality note**

- The analogy is slightly abstract, but not weak enough to require an edit. It still reads as a transferable systems/design framing rather than a crypto-native interpretation.

---

### 5. `clcripto_tldr`

**Verdict:** accepted

**Why it is strong**

- `original_domain` is correctly `crypto`.
- `traditional_equivalent_category` is clear: `tax and legal services`.
- `business_model_analogy` is clean: `regulated advisory service`.
- `transferable_brand_patterns` are useful and grounded:
  - `Category-To-Surface Translation`
  - `Evidence-Bound Behavior`
  - `Block-Structured Strategic Condensation`
- `domain_specific_noise` is correctly separated:
  - `crypto`
  - `fiscalidad cripto`
  - `anonimato`
  - `capital cripto`
- `normalization_status` is `normalized`.

**Quality note**

- This is one of the clearest examples of separating the real source meaning from crypto-native vocabulary.

---

### 6. `meta4_english`

**Verdict:** review-only, not stable

**Why it is weaker**

- `original_domain` is correctly `crypto`, but the underlying source is explicitly experimental.
- `traditional_equivalent_category` is usable: `investment strategy and cultural fund positioning`.
- `business_model_analogy` is plausible: `asset management / thesis-led advisory`.
- `transferable_brand_patterns` are still valid, but this case is the most likely to over-suggest maturity if it is treated like a normal corpus record:
  - `Category-To-Surface Translation`
  - `Evidence-Bound Behavior`
  - `Claim / Signal Gap`
- `domain_specific_noise` is correctly isolated:
  - `crypto-cultural`
  - `digital assets`
  - `investment vehicles`
  - `symbolic belonging`
- `normalization_status` is correctly `needs_human_review`.

**Why it stays review-only**

- The record is a strategy experiment, not a validated deliverable.
- The analogy is close enough to the source domain that it can sound more market-real than the evidence supports.
- It is useful as a controlled example of overreach boundaries, but not as a stable hint source.

**Recommended edits**

- Keep the record in `needs_human_review`.
- Do not use it as a stable narrative hint source.
- If it is ever promoted later, tighten the analogy wording so it is clearly framed as exploratory, not validated.

## Accepted records

The following records are accepted for the normalized corpus:

- `rosalind_brand3_landing`
- `nektar_summary_brand_platform`
- `esco_token_brand_platform_v3`
- `blockdyne_master_brand3`
- `clcripto_tldr`

## Records needing edits

Only one record needs further editorial caution:

- `meta4_english`

The record itself is valid, but it should remain review-only and should not be used as a stable hint source.

## Corpus-level findings

### Weak analogies

- No record contains a broken analogy.
- `blockdyne_master_brand3` is slightly abstract, but still acceptable.
- `meta4_english` has the weakest analogy because it is closest to the source domain and can overstate maturity if treated as a normal corpus example.

### Crypto language leakage into transferable patterns

- No pattern name is crypto-native.
- Crypto/web3 terms are being held in `domain_specific_noise`, not in `transferable_brand_patterns`.
- That separation is working as intended.

### Duplicated patterns

The repeated patterns are not a problem:

- `Category-To-Surface Translation` appears in multiple records because it is a core transferable reading lens.
- `Evidence-Bound Behavior` appears in multiple records because it is the main constraint pattern.
- `Claim / Signal Gap` appears where the record makes a stronger claim than the visible proof can support.

These are intentional repeats, not near-duplicate pattern errors.

### Vague pattern refs

- None of the current `pattern_refs` are vague enough to remove.
- The low-confidence pattern refs are appropriately bounded by evidence and do not overclaim.

### Normalization status

- Five records are properly normalized.
- One record is explicitly `needs_human_review`.
- That is the correct shape for the current corpus.

## Readiness for expansion batch 2

**Conditionally ready.**

The corpus is ready for batch 2 if the next batch continues the same rules:

- keep stable hints limited to `normalized` records
- keep `needs_human_review` records out of stable hint generation
- keep crypto/web3 vocabulary in `domain_specific_noise`
- require explicit `pattern_refs` with evidence

The only thing that should not be treated as stable is `meta4_english`. Everything else is usable as-is for controlled expansion.

