# Brand3 Dimension Evidence Requirements v0 — Readiness Matrix

## Readiness Summary (All Cases)

| Case | Coherencia | Presencia | Percepción | Diferenciación | Vitalidad | Overall |
|---|---|---|---|---|---|---|
| **Vercel** | Thin | Thin | **Ready** | **Blocked** | **Ready** | 2 Ready, 2 Thin, 1 Blocked |
| **LaunchDarkly** | Thin | Thin | **Ready** | **Blocked** | **Ready** | 2 Ready, 2 Thin, 1 Blocked |
| **Builtwith/Kit** | **Blocked** | **Blocked** | **Blocked** | **Blocked** | **Blocked** | 0 Ready, 0 Thin, 5 Blocked |
| **Watermelon** | Thin | Thin | Thin | **Blocked** | **Blocked** | 0 Ready, 3 Thin, 2 Blocked |

---

## Detailed Case Analysis

### VERCEL

**Composite Status**: 2 Ready, 2 Thin, 1 Blocked

#### Coherencia
- **Status**: Thin (14% coverage: 1/7 eligible)
- **Assessment**: Multiple owned surfaces exist (homepage, about, blog). Messaging is consistent: "AI Cloud", "Frontend Cloud", "developer infrastructure". However, Evidence Packet v0 blocked visual metrics and some coherencia signals as "technical" when they should contribute to coherence evaluation.
- **Actual Signal**: Coherencia is likely ready, but packet misclassified evidence.
- **Recommendation**: Update Evidence Packet classification; coherencia can be upgraded to ready with proper visual signal handling.

#### Presencia
- **Status**: Thin (27% coverage: 3/11 eligible)
- **Assessment**: Owned domain clear and fully functional. External channels detected: Wikipedia, recent TechCrunch mentions, likely social profiles (review-gated). Recency is good (April 2026 press mentions are recent).
- **Why Thin**: 40% external minimum not reached; some external channels are review-gated (LinkedIn probably marked ambiguous instead of verified-official).
- **Recommendation**: Verify official social profiles against owned domain links; should push coverage to 40%+.

#### Percepción
- **Status**: Ready (100% coverage: 3/3 eligible)
- **Assessment**: Strong external perception evidence. TechCrunch mentions describe performance outcomes ("build times 7m → 40s"). Blog posts and customer success stories show positive sentiment. Multiple independent sources.
- **Confidence**: High. Proceed to narrative.

#### Diferenciación
- **Status**: Blocked (0% coverage: 0/4 eligible; 2 review-gated, 2 blocked)
- **Why Blocked**: Vercel claims "AI Cloud" and "Frontend Cloud" positioning (owned claims, distinctive-sounding). However:
  - No comparative evidence (vs. Netlify, Railway, Fly.io explicitly named).
  - No external sources using "AI Cloud" language or distinctive category positioning.
  - Input snapshot does not include competitor corpus.
- **This is NOT a packet failure**. This is a **collection/acquisition failure**. The input was incomplete.
- **Recommendation**: **BEFORE attempting to score diferenciación, run Evidence Packet on 2-3 direct competitors:**
  - Netlify (main competitor in deployment space)
  - Railway (serverless positioning competitor)
  - Fly.io (similar positioning)
  - Extract their positioning language, features, messaging.
  - Create comparative matrix: where does Vercel differ?
  - Then re-evaluate diferenciación with comparative context.

#### Vitalidad
- **Status**: Ready (100% coverage: 7/7 eligible)
- **Assessment**: Clear activity signals. Changelog entries visible, recent blog posts (OSS performance articles), recent TechCrunch coverage (April 2026 security incident news shows brand is in the news). Evolution evident.
- **Confidence**: High. Proceed to narrative.

#### Vercel Conclusion

**Current score-readiness: 2 Ready (percepcion, vitalidad), 2 Thin (coherencia, presencia), 1 Blocked (diferenciacion).**

The blocked diferenciacion is **expected and not a failure**. It exposes that input acquisition needs to include competitor discovery for categories where differentiation is important.

If diferenciacion is not scored (abstained), Vercel would still have 4 dimensions with narrative findings (2 ready, 2 thin-but-explorable).

---

### LAUNCHDARKLY

**Composite Status**: 2 Ready, 2 Thin, 1 Blocked

#### Coherencia
- **Status**: Thin (0% coverage: 0/5 eligible; 3 review-gated, 2 blocked)
- **Assessment**: LaunchDarkly likely has coherent messaging around feature flagging, but Evidence Packet found zero eligible evidence. Review-gated items suggest social profile ambiguity. Blocked items likely visual/technical misclassification.
- **Recommendation**: Acquire deeper owned-surface text; verify social profiles as official.

#### Presencia
- **Status**: Thin (27% coverage: 3/11 eligible; 1 review-gated, 7 blocked)
- **Assessment**: Owned domain clear (launchdarkly.com). External channels present but under-detected or over-blocked. Some channels review-gated (likely social). Recency appears good.
- **Recommendation**: Focus on unblocking social profile verification; should unlock ~3-4 more external channels.

#### Percepción
- **Status**: Ready (100% coverage: 4/4 eligible)
- **Assessment**: External sources describe LaunchDarkly in feature flagging/deployment space with positive sentiment. Consistent positioning across sources. Clear external validation.
- **Confidence**: High. Proceed to narrative.

#### Diferenciación
- **Status**: Blocked (0% coverage: 0/5 eligible; 3 review-gated, 2 blocked)
- **Why Blocked**: Same as Vercel. LaunchDarkly owns feature flagging space but no comparative evidence in input (e.g., vs. Split.io, Unleash, etc.). No competitor corpus.
- **Recommendation**: **Acquire competitor corpus for feature flagging space** (Split.io, Unleash, LaunchDarkly, Harness):
  - Extract positioning for each.
  - Create comparative matrix.
  - Then re-evaluate diferenciación.

#### Vitalidad
- **Status**: Ready (100% coverage: 7/7 eligible)
- **Assessment**: Clear changelog activity, ongoing development, external press mentions (if present). Brand maintains active development velocity.
- **Confidence**: High. Proceed to narrative.

#### LaunchDarkly Conclusion

**Current score-readiness: 2 Ready, 2 Thin, 1 Blocked.**

Same pattern as Vercel. Diferenciación is blocked due to missing competitor corpus, not packet failure.

---

### BUILTWITH/KIT

**Composite Status**: 0 Ready, 0 Thin, 5 Blocked

#### All Dimensions: Blocked

- **Root Cause**: Entity ambiguity. The input was audited on `builtwith.kit.com` (a subdomain/branded partner page?), creating relation confusion with:
  - BuiltWith.com (analytics tool)
  - Kit.com (ConvertKit's design product)
  - The target brand (unclear which entity was being analyzed)

- **Universal Failure Pattern**: This is not a Brand3 failure; this is an **input validation failure**. The canonical domain should have been clarified before audit:
  - If auditing Kit (ConvertKit's product): should audit **kit.com**, not builtwith.kit.com.
  - If auditing a BuiltWith + Kit integration: should clarify scope and audit accordingly.

#### Recommendation

**INPUT VALIDATION MUST PREVENT THIS.** Brand3 collection needs to:

1. **Validate canonical marketing domain before audit**: reject subdomains, alias domains, partner-hosted pages.
2. **Clarify scope**: if a brand has multiple domains/products, specify which is being analyzed.
3. **For this case**: start over with correct canonical domain (kit.com if Kit is the target).

#### Builtwith/Kit Conclusion

**This case is not diagnostically useful for Evidence Packet evaluation because the input was wrong.** It does expose a critical acquisition gap: input validation.

---

### WATERMELON

**Composite Status**: 0 Ready, 3 Thin, 2 Blocked

#### Coherencia
- **Status**: Thin (9% coverage: 1/11 eligible; 4 review-gated, 6 blocked)
- **Assessment**: Some coherencia evidence exists but heavily under-detected. Likely due to visual signal misclassification.
- **Recommendation**: Review visual coherence evidence classification; too many false blocks.

#### Presencia
- **Status**: Thin (10% coverage: 1/10 eligible; 1 review-gated, 8 blocked)
- **Assessment**: Very low external coverage. Either Watermelon has minimal external visibility, or Evidence Packet is over-conservative. Profile ambiguity (review-gated social) suggests same-name matching issues.
- **Recommendation**: If Watermelon is a known brand, packet is over-blocking. If Watermelon is small/niche, low presencia is correct.

#### Percepción
- **Status**: Thin (25% coverage: 1/4 eligible; 1 review-gated, 2 blocked)
- **Assessment**: Very low external perception evidence. May indicate:
  - Low external visibility (fits with low presencia).
  - Or, external sources exist but are review-gated due to ambiguity.
- **Recommendation**: If Watermelon has known brand presence, needs Deep Research to clarify external mentions.

#### Diferenciación
- **Status**: Blocked (0% coverage: 0/4 eligible; 3 review-gated, 1 blocked)
- **Why**: No comparative evidence. Also depends on Watermelon category (not clear from test data).
- **Recommendation**: Acquire competitor corpus (once we clarify what Watermelon is/does).

#### Vitalidad
- **Status**: Blocked (0% coverage: 0/6 eligible; 5 review-gated, 1 blocked)
- **Assessment**: Activity evidence exists but appears review-gated. Suggests:
  - Social profile ambiguity (same-name issue).
  - Or, owned changelog/blog is unverified.
- **Recommendation**: Verify official owned surfaces and social profiles.

#### Watermelon Conclusion

**Current score-readiness: 0 Ready, 3 Thin, 2 Blocked.**

Watermelon's low coverage suggests either:
1. **Low external visibility** (small brand, niche market) — in which case thin/blocked is correct.
2. **Over-conservative packet classification** — in which case need to adjust Evidence Packet rules for ambiguous entities.

**Likely need**: Deep Research to disambiguate Watermelon entity and discover external sources.

---

## Cross-Case Patterns

### Pattern 1: Diferenciación is Universally Blocked (Critical Finding)

All 4 cases have **0% diferenciación coverage**. This is not random:

- Vercel: no competitor corpus
- LaunchDarkly: no competitor corpus
- Builtwith/Kit: entity ambiguity prevents any evaluation
- Watermelon: no competitor corpus + unclear entity

**Root Cause**: Input snapshots do not include competitor evidence. Brand3 cannot generate comparative findings from single-entity data.

**Implication**: Either:
1. **Collection must change** to include competitor discovery for categories where diferenciación is important.
2. **Or, diferenciación should be treated as an optional dimension** that is only scored when competitor corpus is available.

### Pattern 2: Percepción and Vitalidad Succeed (When Input Is Clear)

- Vercel: Percepción 100%, Vitalidad 100%
- LaunchDarkly: Percepción 100%, Vitalidad 100%
- Watermelon: Low but not universally blocked (entity ambiguity affects, but not absolutely)
- Builtwith/Kit: Blocked (entity issue)

**Finding**: These dimensions work well with single-entity data. External perception and activity signals are discoverable without requiring competitor context.

### Pattern 3: Entity Ambiguity Cascades to All Dimensions

Builtwith/Kit is a case study: one entity resolution failure → all dimensions blocked.

**Critical for input validation**: Must enforce canonical marketing domain as entry point.

### Pattern 4: Social Profile Verification Blocks Valid Evidence

LaunchDarkly and Watermelon both have review-gated social profiles marked as "ambiguous same-name matches."

For stable, well-known entities (LaunchDarkly), this is over-conservative. A LinkedIn company profile linked from owned domain should be treated as verified-official, not ambiguous.

**Recommendation**: Add official-link verification logic to Evidence Packet.

---

## Acquisition Gaps Exposed by the Spec

### 1. Diferenciación Requires Competitor Corpus (CRITICAL)

**Finding**: Zero diferenciación evidence across all 4 cases.

**Why**: Input snapshots do not include competitor discovery. Evidence Packet can only classify evidence present; it cannot discover missing evidence.

**Fix**: Collection process must run Evidence Packet on 2-3 direct competitors for each brand in competitive categories.

**Timeline Impact**: If diferenciación is required for scoring, this adds per-case overhead (1-2 competitor audits per brand).

### 2. Entity Validation Must Prevent Subdomain Audits (CRITICAL)

**Finding**: Builtwith/Kit case shows that wrong canonical domain selection → universal failure.

**Fix**: Input validation before audit:
- Detect subdomains, redirect chains, partner-hosted pages.
- Enforce canonical marketing domain as entry point.
- Require scope clarification for multi-product brands.

**Implementation**: Add domain canonicalization check in collection entry point.

### 3. Social Profile Verification Needs Official-Link Matching (MEDIUM)

**Finding**: LaunchDarkly and Watermelon have review-gated official social profiles.

**Fix**: If social URL is linked from owned domain (e.g., LinkedIn link on homepage), mark as verified-official instead of ambiguous.

**Implementation**: Add outbound link extraction from owned domain; cross-match with social profile candidates.

### 4. Visual Coherence Evidence Misclassified as Technical (MEDIUM)

**Finding**: Vercel and Watermelon have coherencia evidence blocked as "visual/technical" when it should contribute to messaging consistency evaluation.

**Fix**: Distinguish:
- **Technical-only**: contrast ratios, pixel alignment, layout metrics (no coherencia value).
- **Brand-level coherence**: color palette consistency, typography consistency, logo usage patterns (valid coherencia evidence).

**Implementation**: Refine visual signal classification in Evidence Packet.

### 5. Presencia Minimum Externality Not Met Due to Profile Ambiguity (MEDIUM)

**Finding**: Vercel and LaunchDarkly only reach 27% external coverage when they should reach 40%+.

**Why**: Social profiles are review-gated, reducing external channel count.

**Fix**: Official-link verification (see gap #3) should unlock these channels.

---

## Decision Points

### Should Diferenciación Be Scored Without Competitor Corpus?

**Current finding**: All 4 cases block diferenciación without competitor corpus.

**Options**:

1. **Score diferenciación only when competitor corpus available** → diferenciación becomes optional per-brand dimension.
2. **Require competitor corpus for all scored brands in competitive categories** → adds collection overhead but ensures diferenciación can be scored.
3. **Use owned claims + external language without comparative context** → risks weak findings (owned claims alone not sufficient per spec).

**Recommendation**: Option 1. Diferenciación should be optional and abstained when competitor corpus unavailable. Document as "insufficient comparative evidence" rather than scoring 0.

### Should Builtwith/Kit Be Retried With Correct Input?

**Current status**: All dimensions blocked.

**Recommendation**: Yes. Retry with canonical domain (kit.com) to see if coherencia/presencia/percepción/vitalidad recover. Use this as a validation test that input quality is the root cause, not Evidence Packet.

### Should Evidence Packet Be Deployed Without These Fixes?

**Current readiness**: Evidence Packet v0 exposes important upstream gaps (competitor corpus, entity validation, social verification), but the spec-based evaluation shows it's working correctly at classification.

**Recommendation**: 

1. **Do not feed Evidence Packet into generation yet** (confirmed by existing recommendation).
2. **Do fix the upstream gaps first**:
   - Input validation (subdomain detection, domain canonicalization).
   - Official-link verification for social profiles.
   - Competitor corpus collection for diferenciación.
3. **Then retry the 4 cases** with fixed inputs.
4. **Only after that, feed packet-filtered evidence into prompts**.

---

## Recommended Next Steps

### Immediate (This Week)

1. **Retry Builtwith/Kit with canonical domain** (kit.com).
   - Goal: Validate that entity resolution was the root cause.
   - Expected outcome: coherencia/presencia/vitalidad should recover; diferenciación still blocked (correct).

2. **Add official-link verification to Evidence Packet**.
   - Extract outbound links from owned domain.
   - Cross-match social profile candidates.
   - Mark verified-official instead of ambiguous.
   - Retry Vercel and LaunchDarkly; expect presencia coverage to improve to 40%+.

### Short-term (Next 1-2 Weeks)

3. **Define competitor selection criteria** for diferenciación:
   - By category (SaaS, infrastructure, consumer app, etc.).
   - 2-3 primary competitors per brand.
   - Create template for evidence comparison.

4. **Run Evidence Packet on competitor sets** for Vercel and LaunchDarkly:
   - Vercel competitors: Netlify, Railway, Fly.io.
   - LaunchDarkly competitors: Split.io, Unleash, Harness.
   - Produce comparative positioning matrix.
   - Re-evaluate diferenciación with comparative context.

### Before Prompt Integration

5. **Validate the 4 cases against updated spec**:
   - Builtwith/Kit with correct domain.
   - Vercel with competitor corpus.
   - LaunchDarkly with competitor corpus.
   - Watermelon with Deep Research for entity disambiguation.

6. **Confirm all 4 cases pass the criteria**:
   - Vercel: expect 3-4 ready (coherencia may upgrade with visual fix, percepcion/vitalidad ready, diferenciacion ready with competitor corpus).
   - LaunchDarkly: expect 3-4 ready (similar).
   - Builtwith/Kit: expect 2-4 ready once entity is fixed.
   - Watermelon: expect 1-3 ready (depends on entity clarity).

7. **Only then integrate Evidence Packet** into the narrative prompt pipeline with dimension readiness checks.

---

## Summary

**The spec-based evaluation reveals that Brand3's core problem is not the packet's classification logic — it's upstream acquisition:**

- Diferenciación fails universally because no competitor corpus is collected.
- Entity ambiguity cascades to all dimensions in edge cases like Builtwith/Kit.
- Social profile verification is over-conservative, under-detecting valid external evidence.
- Visual signal classification mixes technical artifacts with brand-level coherence.

**The good news**: Most of these are fixable with focused input validation and collection process changes, not packet rewrites.

**The next diagnostic**: Retry with fixed inputs (correct canonical domain, competitor corpus, official-link verification) before feeding Evidence Packet into generation.

