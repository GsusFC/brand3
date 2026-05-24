# Brand3 Dimension Evidence Requirements v0 — Navigation & Next Steps

**Specification status**: Complete. Ready for implementation planning.

**All artifacts created**:
1. `brand3_dimension_evidence_requirements_v0.md` — Full specification (479 lines)
2. `brand3_dimension_evidence_requirements_v0.json` — Machine-readable schema (529 lines)
3. `brand3_dimension_evidence_requirements_v0_readiness_matrix.md` — Case analysis (367 lines)
4. `brand3_dimension_evidence_requirements_v0_SUMMARY.md` — Executive summary (331 lines)

**Total: 88 KB, 1706 lines of specification.**

---

## Reading Order (Choose Your Path)

### Path A: Decisions First (5 min read)

1. **Start**: This file (navigation).
2. **Read**: `brand3_dimension_evidence_requirements_v0_SUMMARY.md` — overview, findings, decision points.
3. **If decision-making**: Review JSON file's `test_cases` section for Vercel/LaunchDarkly/Builtwith/Watermelon specific status.
4. **Next**: Decide on options (optional vs. required diferenciación, etc.).

### Path B: Detailed Understanding (20 min read)

1. **Start**: `brand3_dimension_evidence_requirements_v0_SUMMARY.md` — overview.
2. **Read**: `brand3_dimension_evidence_requirements_v0.md` sections 1-4 (overview, coherencia, presencia, percepción).
3. **Focus**: `brand3_dimension_evidence_requirements_v0.md` sections 5-6 (diferenciación, vitalidad) — these are the tricky ones.
4. **Validate**: `brand3_dimension_evidence_requirements_v0_readiness_matrix.md` — see how spec applies to real cases.

### Path C: Implementation Planning (30 min read)

1. **Start**: `brand3_dimension_evidence_requirements_v0_SUMMARY.md` sections on "Critical Path to Production".
2. **Read**: Full dimension contracts in `brand3_dimension_evidence_requirements_v0.md`.
3. **Study**: Case-by-case analysis in `brand3_dimension_evidence_requirements_v0_readiness_matrix.md`.
4. **Reference**: JSON schema in `brand3_dimension_evidence_requirements_v0.json` for Evidence Packet validation rules.

### Path D: Quick Reference (5 min, if you already know Brand3)

Just open `brand3_dimension_evidence_requirements_v0.json` and skip to:
- `dimension_contracts` — the core rules per dimension.
- `test_cases` — what worked/failed on each brand.
- `acquisition_gaps_exposed` — what needs fixing upstream.

---

## Key Sections by Use Case

### "What should diferenciación require?"
→ `brand3_dimension_evidence_requirements_v0.md`, section **4. DIFERENCIACIÓN**
→ `brand3_dimension_evidence_requirements_v0_readiness_matrix.md`, section **Pattern 1: Diferenciación is Universally Blocked**

### "What failed on Builtwith/Kit?"
→ `brand3_dimension_evidence_requirements_v0_readiness_matrix.md`, section **BUILTWITH/KIT**
→ Summary: **Entity ambiguity (wrong canonical domain) cascaded to all dimensions.**

### "Why is Vercel missing diferenciación?"
→ `brand3_dimension_evidence_requirements_v0_readiness_matrix.md`, section **VERCEL: Diferenciación**
→ Summary: **No competitor corpus in input. This is acquisition failure, not packet failure.**

### "What's the full time/effort to fix this?"
→ `brand3_dimension_evidence_requirements_v0_SUMMARY.md`, section **Phase 1: Fix Upstream**
→ Summary: **~4 hours development, ~2-3 weeks calendar time (sequential phases).**

### "How should Evidence Packet's JSON output look?"
→ `brand3_dimension_evidence_requirements_v0.json`, section **evidence_packet_output_schema**

### "Which dimension is least likely to have evidence?"
→ `brand3_dimension_evidence_requirements_v0_readiness_matrix.md`, section **Pattern 1**
→ Answer: **Diferenciación (0% across all 4 cases).**

### "What can score without external evidence?"
→ `brand3_dimension_evidence_requirements_v0.md`, section **Cross-Dimension Rules**
→ Answer: **Only coherencia (if owned surfaces align). All others need external or comparative.**

---

## Critical Implementation Decisions (You Must Decide)

### Decision 1: How Should Diferenciación Be Handled?

**Question**: When competitor corpus is unavailable, should diferenciación:
- A) Be marked `abstain` (dimension not scored)?
- B) Be marked `thin` (score low but render it)?
- C) Be marked `blocked` but escalated for manual review?

**Spec says**: A (abstain) is preferred. Dimension is optional when evidence unavailable.

**Where to decide**: `brand3_dimension_evidence_requirements_v0_SUMMARY.md`, section "Decision 1: How Should Diferenciación Be Handled?"

**Impact**: Affects whether reports have 4 or 5 scored dimensions per brand.

### Decision 2: Should Visual Coherence Evidence Be Allowed?

**Question**: Should brand-level visual consistency (color palette, typography, logo usage) contribute to coherencia scoring?

**Spec says**: Yes. Distinguish from technical metrics (contrast ratios) which are blocked.

**Where to find implementation**: `brand3_dimension_evidence_requirements_v0.md`, section "Coherencia: Disallowed", and Evidence Packet section on visual signal refinement.

**Implementation cost**: ~1 hour.

### Decision 3: When Should Evidence Packet Go Live?

**Minimum viable**: After Phase 1 fixes (input validation, social verification). Can integrate as pre-finding filter.

**Full integration**: After Phase 1 + Phase 2 (competitor corpus workflow) + Phase 3 (validation).

**Spec timeline**: Phase 1 this week, Phase 2 next 1-2 weeks, Phase 3 end of week 2.

**You should decide**: Is early integration acceptable if diferenciación is known to be limited?

---

## What Changes From This Spec

### What Changes to Collection

1. **Input validation**: Add domain canonicalization check (reject subdomains, ambiguous domains).
2. **Competitor corpus workflow**: Define competitor selection per category; run Evidence Packet on 2-3 competitors per brand.
3. **Deep Research triggers**: Add heuristics (low presencia, entity ambiguity, or high-value brands) → escalate for Deep Research.

### What Changes to Evidence Packet

1. **Dimension coverage checks**: Output per-dimension readiness status (ready/thin/blocked/insufficient_input).
2. **Official social verification**: Cross-match outbound links from owned domain; verify social profiles.
3. **Visual signal refinement**: Distinguish brand-level visual consistency from technical metrics.
4. **Scoring contract**: Do not pass evidence to prompt without dimension readiness check.

### What Changes to Narrative Engine

1. **Dimension-aware input**: Accept Evidence Packet's dimension coverage output; only prompt on ready dimensions.
2. **Abstention support**: If dimension is blocked/insufficient, do not score that dimension (no finding, no number).
3. **Review-gated evidence handling**: Handle evidence that requires manual review (don't auto-process).

### What Stays the Same

- Scoring rubrics (5 dimensions, 0-100 range).
- Report rendering (layout, HTML template).
- Visual Signature dimension (not affected by this spec).
- Deep Research as escalation path (still available for ambiguous cases).

---

## How to Use This Spec Going Forward

### For Evidence Packet Hardening

1. **Read**: `brand3_dimension_evidence_requirements_v0.json`, section `evidence_packet_validates` for each dimension.
2. **Implement**: Each bullet point becomes a test case or hardening rule.
3. **Validate**: Run against 4 test cases; all should improve or stay stable.

### For Collection Process Updates

1. **Read**: Each dimension's section "collection_must_provide".
2. **Update**: Input collection workflow to acquire specified evidence types.
3. **Example**: Diferenciación needs competitor corpus → add competitor discovery step.

### For Narrative Engine Integration

1. **Read**: JSON section `scoring_decision` schema.
2. **Implement**: Per-dimension readiness check before prompting.
3. **Test**: Run Vercel; expect percepcion + vitalidad + (coherencia/presencia with fixes) to pass; diferenciacion to block.

### For Report Rendering

1. **Question**: Should report render abstained dimensions as "skipped" or hide them entirely?
2. **Answer**: Depends on editorial choice. Spec recommends showing which dimensions were scored and which abstained.
3. **Example**: "Vercel: 4 of 5 dimensions scored (diferenciación requires competitive context)."

---

## Immediate Next Steps (After You Decide)

### This Week (Phase 1 — Upstream Fixes)

- [ ] **Input Validation**: Add domain canonicalization (reject subdomains, follow redirects, enforce root domain).
- [ ] **Social Verification**: Add outbound link matching (extract homepage links; cross-match with social profiles).
- [ ] **Visual Refinement**: Distinguish brand-level visual signals from technical metrics.
- [ ] **Retry Vercel/LaunchDarkly**: Expect presencia improvement (27% → 40%+), coherencia improvement.

### Next 1-2 Weeks (Phase 2 — Acquisition & Competitor Corpus)

- [ ] **Competitor Corpus Workflow**: Define per-category competitor selection (SaaS, infrastructure, consumer, etc.).
- [ ] **Create Comparison Template**: Matrix format for extracting competitive positioning.
- [ ] **Run on Competitors**: Vercel (vs. Netlify, Railway, Fly.io); LaunchDarkly (vs. Split.io, Unleash, Harness).
- [ ] **Evaluate Diferenciación**: With competitor context, diferenciación should move from blocked → ready/thin.

### Week 2-3 (Phase 3 — Validation & Integration)

- [ ] **Retry Builtwith/Kit**: With correct domain (kit.com); verify entity resolution was root cause.
- [ ] **Validate 4 Cases Against Spec**: All should score ≥3 of 5 dimensions ready/thin.
- [ ] **Deep Research Watermelon**: If still unclear, trigger Deep Research for entity disambiguation.
- [ ] **Wire Evidence Packet Into Narrative**: Add dimension coverage checks; only pass ready evidence to prompt.
- [ ] **Test Report Generation**: Render reports with abstained dimensions explicitly marked.

### Decision Checkpoints

- **End of Phase 1**: Can you confirm input validation prevents subdomains + social profiles verify?
- **End of Phase 2**: Can you confirm competitor corpus workflow is defined and working?
- **End of Phase 3**: Can you confirm all 4 cases either pass validation or fail for documented reasons (entity issue, etc.)?

---

## Questions to Answer Before Coding

1. **Diferenciación handling**: Optional dimension (abstain when no competitor corpus) or required (must collect competitors for all brands)?

2. **Visual evidence**: Is brand-level visual consistency (palette, typography) part of coherencia measurement, or excluded?

3. **Presencia minimum**: Is 40% external coverage the right threshold, or should it vary by brand type?

4. **Abstention rendering**: How should reports handle abstained dimensions? Skip from report? Show as "data unavailable"? Show as "not evaluated in this run"?

5. **Watermelon deep research**: Worth triggering Deep Research for low-visibility brands, or accept thin/blocked status as valid?

6. **Builtwith/Kit retry**: After fixes, should it be retried to validate, or deprioritize as edge case?

**These decisions should be made before Phase 1 implementation starts.**

---

## File Structure Summary

```
Specification (complete):
├── brand3_dimension_evidence_requirements_v0.md (479 lines)
│   └── Full contracts: goal, ready/thin/blocked, allowed/disallowed, etc.
│
├── brand3_dimension_evidence_requirements_v0.json (529 lines)
│   ├── dimension_contracts (per-dimension full spec)
│   ├── evidence_packet_output_schema (what packet should output)
│   ├── test_cases (Vercel, LaunchDarkly, Builtwith, Watermelon analysis)
│   ├── acquisition_gaps_exposed (critical findings)
│   └── validation_rules (hardening criteria for Evidence Packet)
│
├── brand3_dimension_evidence_requirements_v0_readiness_matrix.md (367 lines)
│   ├── Readiness summary matrix (all 4 cases)
│   ├── Detailed case analysis (why each dimension blocked/thin/ready)
│   ├── Cross-case patterns (universal failures, what worked)
│   ├── Acquisition gaps (what needs fixing upstream)
│   ├── Decision points (should diferenciación be scored? etc.)
│   └── Recommended next steps (phased implementation plan)
│
└── brand3_dimension_evidence_requirements_v0_SUMMARY.md (331 lines)
    ├── Key findings (Evidence Packet works; upstream fixes needed)
    ├── Readiness summary (ready/thin/blocked per case)
    ├── Critical path to production (phases 1-4)
    ├── Decision points (three options per decision)
    └── Conclusion (timeline, effort, focus areas)
```

---

## Version & Change Tracking

**This specification: v0** (first complete version).

**Based on**: Evidence Packet v0 test results on 4 brands; diagnostic review of Builtwith/Kit; cuestionario de taxonomía original.

**Next versions**: Expected after Phase 3 validation (v0.1 with adjustments based on implementation).

---

## Sign-Off

**Specification is complete and ready for decision-making and implementation planning.**

Recommend: Schedule 1-hour review of SUMMARY.md + decision meeting before starting Phase 1.

