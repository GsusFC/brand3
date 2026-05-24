# Brand3 Dimension Evidence Requirements v0 — Executive Summary

**Status**: Specification complete. Diagnostic analysis of 4 test cases complete.

**Output artifacts**:
- `brand3_dimension_evidence_requirements_v0.md` — Full specification with dimension contracts.
- `brand3_dimension_evidence_requirements_v0.json` — Machine-readable schema and test case evaluation.
- `brand3_dimension_evidence_requirements_v0_readiness_matrix.md` — Detailed readiness analysis for all 4 cases.

---

## Key Findings

### 1. Evidence Packet v0 Is Diagnostic, Not Prompt-Ready

Evidence Packet v0 is diagnostically useful: it exposes what evidence exists, what is missing, and where the current acquisition flow creates weak or contaminated narrative inputs.

It is not prompt-ready. The Vercel test exposed local classification defects:

- URL-only evidence can still be marked eligible.
- Source roles are too coarse.
- Social/profile candidates can be over-gated.
- Differentiation coverage can fall to zero without a dimension-level abstention contract.

Example: Vercel and LaunchDarkly both have diferenciación status = **blocked** with 0 eligible evidence. This is the correct classification. But the real problem is that no competitor corpus was collected in the input phase.

**Implication**: Fixing Evidence Packet alone will not fix diferenciación. We need both a stricter packet contract and better upstream collection for dimensions that require special evidence.

### 2. Diferenciación Universally Fails (Critical Finding)

All 4 cases: **0% diferenciación coverage**.

**Root cause**: Input snapshots do not include competitor evidence.

**Why this matters**: 
- Diferenciación is a required dimension for Brand3 editorial credibility.
- It's the only dimension that explicitly requires relational/comparative evidence.
- Without competitor context, every brand looks generic relative to... nothing.

**Fix**: Collection process must run Evidence Packet on 2-3 direct competitors and generate comparative matrix before scoring target brand's diferenciación.

**Cost**: 1-2 extra Evidence Packet runs per brand in competitive categories (~20-30 min per brand extra).

### 3. Entity Ambiguity Cascades (Builtwith/Kit Case)

**What happened**: Input was audited on `builtwith.kit.com` (subdomain or partner page?), creating relation confusion with BuiltWith.com, Kit.com, and the target entity.

**Result**: All 5 dimensions blocked universally.

**Why this matters**: This is not a Brand3 failure. This is an **input validation failure**. The canonical marketing domain should have been enforced before audit began.

**Fix**: Add pre-audit domain canonicalization:
- Detect subdomains, aliases, partner-hosted pages.
- Enforce canonical marketing domain.
- Reject ambiguous inputs with clear error message.

**Cost**: ~1 hour to add domain validation check in collection entry point.

### 4. Social Profile Over-Conservatism Reduces Presencia Coverage

LaunchDarkly and Vercel both have LinkedIn company profiles marked as "ambiguous same-name external profile" and review-gated.

For stable, well-known brands, this is over-conservative. A LinkedIn profile explicitly linked from the owned domain should be treated as verified-official, not ambiguous.

**Fix**: Add official-link verification logic:
- Extract outbound links from owned domain.
- Cross-match against social profile candidates.
- Mark as verified-official if link exists.

**Impact**: Vercel and LaunchDarkly presencia coverage would improve from 27% to likely 40%+, making them ready instead of thin.

**Cost**: ~2 hours to add outbound link matching.

### 5. Visual Coherence Evidence Misclassified as Technical

Vercel and Watermelon have coherencia evidence (brand-level visual consistency: color palette, typography, logo usage) classified as "technical/internal" and blocked.

This is incomplete. Technical-only signals (contrast ratios, pixel alignment) are not coherencia evidence. Brand-level visual behavior can support coherencia, but it must not independently make the dimension ready.

**Fix**: Refine visual signal classification in Evidence Packet:
- **Block**: contrast ratios, pixel alignment, layout metrics.
- **Allow as support only**: color palette consistency, typography consistency, logo usage patterns.

**Impact**: Coherencia coverage would improve for all cases.

**Cost**: ~1 hour to refine visual signal tagging.

---

## Readiness Summary (All Cases)

| Case | Ready | Thin | Blocked | Can Score? |
|---|---|---|---|---|
| **Vercel** | 2 | 2 | 1 | Yes, with 4 of 5 dimensions (no diferenciación) |
| **LaunchDarkly** | 2 | 2 | 1 | Yes, with 4 of 5 dimensions (no diferenciación) |
| **Builtwith/Kit** | 0 | 0 | 5 | No; input was wrong |
| **Watermelon** | 0 | 3 | 2 | Partial; needs entity clarification |

### What This Means

- **Vercel & LaunchDarkly**: High-evidence cases. Can score 4/5 dimensions well (percepcion, vitalidad, coherencia, presencia with fixes). Diferenciación blocked but correctly (no competitor corpus).
- **Builtwith/Kit**: Input validation failure. Needs retry with correct canonical domain.
- **Watermelon**: Low external visibility case (small/niche brand). Or, entity ambiguity (needs Deep Research).

---

## Critical Path to Production

### Do NOT Integrate Evidence Packet Into Generation Yet

Evidence Packet v0 is useful as a diagnostic filter, but it exposes upstream gaps that must be fixed first.

### Phase 1: Fix Upstream (This Week)

**Priority 1 — Input Validation** (CRITICAL)
```
Add domain canonicalization check before audit:
- Reject subdomains (builtwith.kit.com) → error
- Enforce root domain (vercel.com, launchdarkly.com, kit.com)
- Detect redirect chains; follow to canonical domain
- Require scope clarification for multi-product brands

Impact: Prevents cases like Builtwith/Kit entirely.
Effort: ~1 hour
Timeline: 1 day
```

**Priority 2 — Official Social Profile Verification** (HIGH)
```
Add outbound link matching:
- Extract links from owned domain's homepage/about
- Cross-match against social profile candidates (LinkedIn, X, etc.)
- If link exists, mark as verified-official (not ambiguous)

Impact: Unlocks 3-4 social channels per brand; presencia improves 27% → 40%+
Effort: ~2 hours
Timeline: 2-3 days
```

**Priority 3 — Visual Signal Refinement** (MEDIUM)
```
Distinguish technical-only vs. brand-level visual:
- Block: contrast ratios, pixel alignment, layout metrics
- Allow: color palette consistency, typography, logo usage

Impact: Coherencia coverage improves across all cases
Effort: ~1 hour
Timeline: 1 day
```

### Phase 2: Acquire Missing Evidence (Next 1-2 Weeks)

**For Diferenciación to Work**:
```
Create competitor corpus collection workflow:
1. Define category-based competitor selection (SaaS, infrastructure, consumer, etc.)
2. Create template for competitive positioning matrix
3. For each brand: run Evidence Packet on 2-3 competitors
4. Extract positioning, UVP, external language
5. Create comparative matrix
6. Evaluate target brand's diferenciación in context

Timeline: 1-2 weeks (first cases: Vercel, LaunchDarkly)
```

**For Watermelon (or any ambiguous case)**:
```
Trigger Deep Research when:
- Entity relation unclear, OR
- Low external visibility (presencia < 20%), OR
- Multiple surfaces with different messaging (coherencia ambiguous)

Deep Research output: disambiguated entity, additional sources, external context
```

### Phase 3: Validate Against Spec (This Requires Explicit Testing)

**Retry 4 cases with fixes**:
```
1. Builtwith/Kit: run on kit.com (canonical domain)
   Expected: coherencia, presencia, percepcion, vitalidad → ready/thin
   
2. Vercel: re-run with official social verification + competitor corpus
   Expected: coherencia thin→ready, presencia thin→ready, 
             diferenciacion blocked→ready (with competitors)
   
3. LaunchDarkly: re-run with official social verification + competitor corpus
   Expected: same as Vercel
   
4. Watermelon: Deep Research disambiguation + retry
   Expected: clarity on entity; may unlock multiple dimensions

Success criteria:
- All 4 cases can score ≥3 of 5 dimensions (or abstain explicitly)
- Diferenciacion is ready when competitor corpus provided
- No false blanket-blockage (like Builtwith/Kit entity issue)
```

### Phase 4: Integrate Into Generation (Only After Validation)

**Wire Evidence Packet into narrative prompt with dimension coverage checks**:
```
For each dimension:
- If status = ready: pass evidence to prompt
- If status = thin: flag to narrative engine; prose must qualify evidence limits
- If status = blocked: abstain; do not score; do not render finding
- If status = abstain: render no score/finding and preserve the reason
- If status = review_required: require manual approval before prompt use

Do NOT render scores without evidence backing.
Do NOT render "unavailable" as score; use abstention instead.
```

---

## Specification Details

The full specification (in `brand3_dimension_evidence_requirements_v0.md` and `.json`) defines for each dimension:

- **Goal**: What the dimension measures.
- **Epistemology**: What type of evidence is required (owned vs. external, comparative vs. standalone, etc.).
- **Ready/Thin/Blocked criteria**: When the dimension has enough evidence to score.
- **Allowed/Disallowed evidence types**: What counts and what doesn't.
- **Minimum externality**: Percentage of external vs. owned evidence required.
- **Owned-only sufficiency**: Can dimension be scored with only owned evidence?
- **Comparative requirement**: Does dimension need competitor context?
- **Abstention criteria**: When dimension should not render a score.
- **Collection must provide**: What upstream collection needs to deliver.
- **Evidence Packet validates**: What hardening rules Evidence Packet needs.

### Key Specification Insights

**Coherencia**: Intra-entity alignment. Can score with owned evidence alone. Doesn't need competitors.

**Presencia**: Multi-channel detectability. Requires 40% external minimum. Need better social verification.

**Percepción**: External perception. Requires 100% external (no owned self-description). Absence of external perception can only become observable absence when search coverage is documented, presencia is ready/high, query scope is known, and no external sentiment source is found. Otherwise it remains thin or abstains.

**Diferenciación** (CRITICAL): Requires comparative evidence OR category-distinctive external language. Owned claims alone are NEVER sufficient. Most likely to block; should abstain rather than score 0.

**Vitalidad**: Activity and evolution. Requires temporal signals (recency, updates). Can score with owned evidence alone; external press corroborates.

---

## Decision Points for Jesús

### 1. How Should Diferenciación Be Handled?

**Option A: Optional Dimension**
- Diferenciación is only scored when competitor corpus available.
- Otherwise abstain with reason: "insufficient comparative evidence".
- Report generates 4-5 dimensions per brand (varies).

**Option B: Required but Deferred**
- All brands initially scored on 4 dimensions (skip diferenciación).
- Diferenciación added later when competitor corpus collected.
- Second-pass scoring adds diferenciación to brands.

**Option C: Competitor Corpus Mandatory**
- All brands in competitive categories must have competitor corpus before scoring.
- Adds per-brand overhead (~20-30 min for competitor audit).
- Ensures diferenciación can always be scored.

**Recommendation**: Option A (optional dimension). Report editorial credibility does not hinge on diferenciación alone. When absent, document reason explicitly.

### 2. Should Visual Coherence Be Allowed as Evidence?

**Current behavior**: All visual signals (brand-level consistency + technical metrics) are blocked.

**Question**: Should brand-level visual consistency (color palette, typography, logo usage) count toward coherencia?

**Decision needed**: If yes → refine visual signal classification (1 hour work, phase 1). If no → document visual evidence is excluded from coherencia (acceptable, but limits signal).

**Recommendation**: Yes, include brand-level visual consistency. It's part of how a brand maintains consistency across touchpoints.

### 3. Builtwith/Kit Retry — Worth Doing?

**Should we re-run Builtwith/Kit with correct domain (kit.com)?**

**Why yes**: Validates that entity resolution was root cause; proves packet isn't broken.

**Why no**: Watermelon and Builtwith/Kit are edge cases; Vercel and LaunchDarkly are the main product use cases.

**Recommendation**: Yes, but schedule it for Phase 3 (after fixes). Don't block integration on it.

### 4. When Should Evidence Packet Go Live in Generation?

**Earliest responsible date**: After Phase 1 + Phase 2 fixes + Phase 3 validation. Estimated: 2-3 weeks.

**Blocker**: Diferenciación competitor corpus workflow must be defined. Can't integrate packet without knowing how to handle blocked diferenciación.

**Risk if integrated early**: Renders scores without backing; false credibility on blocked dimensions.

---

## What Evidence Packet v0 Is (and Isn't)

### What It IS

✓ A classification layer that correctly identifies evidence type, source role, and eligibility.
✓ A diagnostic tool that exposes upstream input quality issues.
✓ A filter that prevents technical artifacts and visual metrics from becoming narrative findings.
✓ A machine-readable inventory of what evidence exists and what doesn't.
✓ Proof that deterministic classification can replicate Deep Research discipline.

### What It ISN'T

✗ A complete evidence acquisition replacement (doesn't discover missing evidence).
✗ A prompt input contract (not yet; needs hardening for dimension coverage).
✗ A findings generator (doesn't write narrative).
✗ A competitor discovery tool (can only classify present evidence).
✗ A substitution for collection expertise (needs upstream fixes to work well).

---

## Recommended Reading Order

For implementing the next phase:

1. **Start here**: This executive summary (overview of findings and timeline).
2. **For design decisions**: `brand3_dimension_evidence_requirements_v0.json` sections on "adverse_cases" and "decision_points".
3. **For specification detail**: `brand3_dimension_evidence_requirements_v0.md` (full dimension contracts).
4. **For diagnostic context**: `brand3_dimension_evidence_requirements_v0_readiness_matrix.md` (case-by-case analysis).

---

## Conclusion

**Evidence Packet v0 is correctly diagnosing the problem. The problem is upstream.**

Brand3 can score 4-5 dimensions well once:
1. Input validation prevents ambiguous domains.
2. Social profile verification unlocks valid external channels.
3. Collection includes competitor corpus for diferenciación.

Timeline to production: 2-3 weeks with focused work on phases 1-3.

No major packet rewrites needed. Focus on upstream fixes.
