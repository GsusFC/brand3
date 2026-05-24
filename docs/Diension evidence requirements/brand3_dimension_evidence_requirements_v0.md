# Brand3 Dimension Evidence Requirements v0

**Purpose**: Define the evidence contract each Brand3 dimension must satisfy before evidence can be considered ready for narrative finding generation.

**Status**: Specification upstream of Evidence Packet hardening.

**Data sources**: Evidence Packet v0 tests on Vercel, Builtwith/Kit, LaunchDarkly, Watermelon.

---

## Overview

Each Brand3 dimension operates on a different **evidence epistemology**:

- **Coherencia** (consistency): intra-entity alignment across owned surfaces. Requires multiple owned touchpoints.
- **Presencia** (detectability): multi-channel existence and volume. Requires owned + external surface detection.
- **Percepción** (external perception): how others describe the brand. Requires external sources, not self-description.
- **Diferenciación** (singularity): what distinguishes the brand from competitors. **Requires comparative evidence or category-distinctive external claims.** Owned-only evidence is insufficient.
- **Vitalidad** (activeness): evolution and momentum. Requires temporal activity signals (recency, updates, growth indicators).

### Key Principle

**A dimension is `ready` for narrative generation only when its evidence pool has both sufficient quantity AND the right type of evidence for that dimension's epistemology.** Absence of the right evidence type means the dimension cannot claim ready status — it should abstain from scoring, not score low.

---

## Dimension Contracts

### 1. COHERENCIA

**Evidence Goal**: Detect whether a brand's messaging, tone, visual identity, and positioning are consistent across owned touchpoints where the brand controls the narrative.

**Epistemology**: Intra-entity alignment. Does not require external validation; external silence does not contradict coherence.

#### Ready Requirements

A coherencia dimension is **ready** when:

- **Minimum 2 owned surfaces** exist with distinct purposes (e.g., homepage + about, or homepage + docs, or social bio + blog).
- **Consistent message/positioning/tone** is detectable across those surfaces (not contradictory phrasing, consistent value proposition, aligned audience language).
- **Visual consistency** is observable (color palette, typography, layout patterns similar or intentionally distinct but explained).
- **At least one external source** can verify the owned message claim (optional but strengthens ready status).

**Eligible Evidence Types**:
- Homepage, about page, product pages, docs, blog posts (owned surface text).
- Official social media bios and messaging (LinkedIn, X, etc., if verified as official).
- Brand messaging extracted from multiple owned pages.
- External mentions that echo the brand's claimed positioning (corroboration, not contradiction).

**Disallowed**:
- Visual-only metrics (color counts, contrast ratios, layout stats) — these are technical signals, not messaging evidence.
- Schema/meta tags alone.
- robots.txt, sitemap.xml, llms.txt.
- Self-contradictory owned claims without external perspective.

#### Thin Requirements

Coherencia is **thin** when:

- Only 1 owned surface exists, OR
- Multiple surfaces exist but messaging is vague or generic (boilerplate SaaS language that could apply to any competitor).
- Tone varies wildly but coherence cannot be assessed due to limited surfaces.

#### Blocked

Coherencia is **blocked** when:

- Zero owned surfaces with meaningful text.
- Owned surfaces directly contradict each other in positioning (homepage says "AI platform", about page says "workflow tool", LinkedIn says "productivity suite" — three unrelated categories).
- Evidence is only technical artifacts (robots.txt, schema, etc.).

#### Owned Surfaces and External Corroboration

- **Owned surfaces alone can make coherencia ready** — this is the only dimension where self-description is primary.
- However, **external corroboration strengthens ready status**.
- External sources contradicting the owned claim → need manual review, do not auto-score coherencia as ready.

#### Can Score with Zero Evidence?

**No.** Zero coherencia evidence → abstain. Do not score "unavailable"; do not score 0. Dimension is skipped.

#### Minimum Externality

0% external required for ready status. Coherencia is about owned-surface alignment.

#### What Collection Must Provide

- Multiple owned surfaces for the target domain (not just homepage).
- Text extraction with confidence scores.
- Tone/messaging analysis from owned pages.
- No required external search (if available, useful; if not, coherencia can still be scored).

#### What Evidence Packet v0 Must Validate

- ✓ Owned surfaces are marked correctly (from audited_surface).
- ✓ Technical artifacts (robots.txt, schema) are classified as technical, not coherencia evidence.
- ✓ Visual-only metrics are blocked, not eligible.
- ✓ Minimum 2 surfaces exist for eligible status.
- ✓ Empty-text evidence is blocked.

---

### 2. PRESENCIA

**Evidence Goal**: Detect whether a brand is discoverable and existent across the channels relevant to its market context.

**Epistemology**: Multi-channel detectability. Requires both owned (web presence) and external (mentions, listings, platform profiles) evidence.

#### Ready Requirements

A presencia dimension is **ready** when:

- **Owned web presence**: Canonical domain exists, loads, has content, valid SSL, not a 404 or redirect-to-other-site.
- **Minimum 2 external channels detected** where brand appears (e.g., web + press mention, or web + LinkedIn + GitHub if tech-focused, or web + social + directory listing).
- **Recency**: Last activity on any channel ≤ 90 days (for active brands). For passive categories (e.g., some enterprise software), > 90 days is acceptable if there is current owned-surface evidence.
- **No evidence of abandonment**: Not sitting in a 404 state, not archived, not a domain squatter.

**Eligible Evidence Types**:
- Owned web domain (homepage, key pages, documentation).
- Wikipedia/encyclopedic profile (searchability, category placement).
- News mentions (press release republications, coverage, announcements).
- Official social media profiles (LinkedIn company, X/Twitter if verified).
- Specialized directories (GitHub if tech, Crunchbase if startup, industry-specific listings).
- Recent activity indicators (changelog, blog post, social post, press mention).

**Disallowed**:
- Historical presence only (no recent activity, archived state).
- Unverified social profiles (same-name but unconfirmed accounts).
- Domain squatter or parked domain evidence.
- robots.txt, sitemap.xml alone (these are technical, not presence).
- Marketplace listings (Stripe Apps, Slack App Store) without owner link.

#### Thin Requirements

Presencia is **thin** when:

- Owned web presence exists but only 1 external channel detected.
- Multiple channels exist but activity is > 120 days old.
- Only social presence (no owned web), or only directory listing (no owned web).

#### Blocked

Presencia is **blocked** when:

- No owned web presence (404, no domain, redirect to unrelated site).
- Zero external mentions or profiles.
- Last activity > 1 year ago (appears abandoned).

#### Can Score with Zero Evidence?

**No.** Zero presencia → abstain. Presence is binary: detected or not.

#### Minimum Externality

**Minimum 40% external required for ready status.** Owned web alone is not enough; must have external corroboration (press, directory, or official social).

Formula: `(external_channels_detected / total_channels_detected) ≥ 0.4`

#### What Collection Must Provide

- Owned web domain verification (SSL, HTTP status, content length).
- Multi-channel discovery (web, press, social, directories — context-dependent).
- Recency metadata (last update date, last post date).
- No requirement for deep external research; standard search + social profile checks sufficient.

#### What Evidence Packet v0 Must Validate

- ✓ Owned domain is verified (not 404, not parked).
- ✓ Technical signals (robots.txt, sitemap size) are not presencia evidence.
- ✓ Related surfaces are correctly classified (LinkedIn as external, not alias).
- ✓ Minimum 2 channels with recent activity (≤ 90 days).
- ✓ At least 40% external evidence exists.

---

### 3. PERCEPCIÓN

**Evidence Goal**: Detect what sentiment and themes emerge when external sources describe or mention the brand.

**Epistemology**: External perception. Self-description is not perception; perception requires independent external sources.

#### Ready Requirements

A percepción dimension is **ready** when:

- **Minimum 2 independent external sources** mention the brand with explicit sentiment or theme (e.g., press article, customer review, analyst report, social mention).
- **At minimum, one of those sources is editorial or review-based** (not marketplace listing or auto-aggregated social).
- **Sentiment is detectable** (positive, negative, neutral, mixed) and not just presence.
- **Themes are consistent or explicitly conflicted** (if external sources disagree on sentiment, that's valid percepcion data).

**Eligible Evidence Types**:
- News articles (TechCrunch, industry press, mainstream media).
- Customer reviews (G2, Capterra, ProductHunt, if substantive).
- Analyst reports (Gartner, Forrester, etc.).
- Reddit threads, Hacker News discussions, Twitter mentions with clear sentiment.
- Blog posts by external authors (not brand-owned blog).
- Podcasts, interviews with brand founders (if from external media).

**Disallowed**:
- Owned blog posts, press releases, company statements (these are brand self-description, not external perception).
- Marketplace listings without review data (AppStore listings, software repos without user comments).
- Social media followers/engagement metrics alone (this is presencia, not perception).
- Trust/security scanner signals (ScamAdviser, Joe Sandbox) — these are review-gated security signals, not brand perception.

#### Thin Requirements

Percepción is **thin** when:

- Only 1 external source with sentiment.
- Multiple sources but all from the same domain/publisher.
- Weak sentiment signal (mention without clear opinion).

#### Blocked

Percepción is **blocked** when:

- Zero independent external sources with sentiment.
- Only self-published material (owned blog, press release).

#### Can Score with Zero Evidence?

**Yes, with caveats.** Zero external perception can be meaningful data: it may indicate low visibility, niche positioning, or early stage. However:

- **Absence must be explicitly documented** ("no detectable external perception; brand is not mentioned in searched sources").
- **Score cannot be "unavailable"** — it must reflect that absence itself is the finding (e.g., "no external brand sentiment detected" as observation).
- **This is valid only if presencia is high**. If brand has high presence but zero perception, that's a finding. If brand has low presence AND low perception, confounding is too high; abstain.

#### Minimum Externality

**100% external required.** Owned claims do not count toward percepción. Owned claims can be evidence for other dimensions (coherencia, vitalidad) but not for how external actors perceive.

#### What Collection Must Provide

- External source discovery (news, reviews, social mentions, discussion forums).
- Sentiment extraction from those sources.
- Source role classification (editorial vs. listing vs. aggregator).
- Author affiliation detection (not brand-affiliated).

#### What Evidence Packet v0 Must Validate

- ✓ All percepción evidence is external (no owned blog, no owned social).
- ✓ Minimum 2 independent sources.
- ✓ At least 1 editorial/review source (not marketplace listing alone).
- ✓ Sentiment is explicit (not just presence).
- ✓ Trust/security signals are review-gated, not eligible.

---

### 4. DIFERENCIACIÓN

**Evidence Goal**: Detect whether the brand claims or demonstrates something singular relative to its category or direct competitors.

**Epistemology**: Relational/comparative. A claim is only differentiated if there's a competitor reference or external category-distinctive language.

#### Ready Requirements

A diferenciación dimension is **ready** when:

**ONE of the following conditions is met:**

1. **Direct comparative evidence exists**: Brand is explicitly compared to a named competitor (e.g., "vs. Stripe", "unlike Shopify", "faster than Airtable") in:
   - Owned marketing copy (homepage UVP, ads, docs), AND
   - At least 1 external independent source echoes the claim (press article, review site, customer mention).

2. **Category-distinctive external evidence exists**: Multiple independent external sources (≥ 2) use language that situates the brand uniquely in its category, AND that language is NOT generic category language.
   - Example: "The only platform built for real-time data" (specific, verifiable, category-distinctive).
   - Counter-example: "AI-powered platform for teams" (generic, applies to most competitors).
   - Example: TechCrunch describes Vercel as "the serverless deployment platform favored by Next.js developers" (specific positioning).
   - Counter-example: "cloud infrastructure company" (generic).

3. **Competitor corpus provided by collection**: Evidence Packet v0 or collection process runs the brand against 2+ direct competitors, and Brand3 analysis can extract differentiation from comparative matrix (positioning, features, pricing, audience language).

#### Thin Requirements

Diferenciación is **thin** when:

- Brand has distinctive owned claims (language, positioning) but zero independent external corroboration.
- External sources describe a unique capability but brand does not claim it (accidental differentiation).
- Evidence of differentiation exists but is weak or from single source.

#### Blocked

Diferenciación is **blocked** when:

- **Zero comparative evidence of any kind**.
- **All evidence is owned-only** (brand claims it, no external echo).
- **Evidence is generic category language** ("AI-powered", "mobile-first", "cloud-based") that could describe any competitor.
- **Evidence is about price/scale/maturity, not positioning** (e.g., "bigger than X", "cheaper than Y"). Scale differences are not differentiation in this context; they're commodities.

#### Critical Rule: Owned Claims Alone Are Never Sufficient

**Owned differentiation claims with zero external corroboration must be classified as `thin` or `blocked`, not `ready`.** 

Rationale: A brand can claim anything about itself. Differentiation requires external validation that the claim is actually distinctive relative to alternatives.

#### Can Score with Zero Evidence?

**No.** Zero diferenciación evidence → abstain. Dimension is skipped.

This is the most common failure mode: brands that look generic or unscored on diferenciación should abstain, not score 0. The absence itself is a piece of meta-commentary ("no detectable differentiation") but should not render as a score.

#### Minimum Externality

**Minimum 50% external required for ready status.**

- If using comparative evidence: at least 1 external source must echo the claim.
- If using category-distinctive language: at least 2 external sources must use the language.
- Owned claims alone: 0% eligible.

#### Competitor Corpus Requirement

**When no direct comparative evidence or distinctive external language exists, collection must acquire competitor evidence.**

If diferenciación is `blocked` or `thin` and the brand is in a competitive category, recommend:
- Run Evidence Packet on 2–3 direct competitors.
- Extract their positioning, UVP, external description.
- Create a comparative matrix showing where brand differs.
- Re-evaluate diferenciación with competitor context.

Without this, diferenciación will remain zero for all brands in competitive categories.

#### What Collection Must Provide

- Comparative claims (owned or external, explicit competitor names).
- External sources with category-distinctive positioning language.
- Competitor evidence (if no direct comparative claims found in target brand).
- Source-role tagging for all external claims (news article, review site, customer review, analyst report).

#### What Evidence Packet v0 Must Validate

- ✓ Owned claims are marked as `thin` or `blocked` if no external corroboration.
- ✓ Generic category language ("AI-powered", "cloud-based", etc.) is not counted as differentiation.
- ✓ Comparative evidence has both owned AND external sources.
- ✓ Price/scale/maturity claims are not treated as differentiation.
- ✓ Minimum 50% external evidence for ready status.
- ✓ Dimension coverage check: if all diferenciación evidence is blocked, report `insufficient_comparative_evidence` and abstain.

---

### 5. VITALIDAD

**Evidence Goal**: Detect whether the brand is actively evolving, publishing, and building, or in stasis/abandoned state.

**Epistemology**: Temporal activity. Requires recent/recency signals and evidence of change.

#### Ready Requirements

A vitalidad dimension is **ready** when:

- **Owned activity is recent**: Last update to owned surfaces (homepage, blog, changelog, docs, social) is ≤ 60 days old.
- **Evidence of evolution exists**: At least one of:
  - Changelog entries with version bumps and features (owned changelog, ≤ 90 days).
  - Blog posts or articles announcing updates (owned or external, ≤ 90 days).
  - Social media activity (official social account posts, ≤ 30 days for active brands, ≤ 90 days for quiet but maintained brands).
  - Press mentions of new funding, hires, feature launches (external, ≤ 180 days).
- **Activity is consistent, not spiky**: Evidence shows ongoing development, not a one-off post followed by silence.

**Eligible Evidence Types**:
- Changelog entries with recency (owned changelog, GitHub releases, Releasebot feeds).
- Blog posts announcing features/updates (owned blog, ≤ 90 days).
- Official social posts (LinkedIn, X, if verified owned account).
- Founder/team public activity (new hire announcements, talks, open-source contributions).
- External press mentions (funding, acquisitions, major feature launches).
- GitHub activity (for tech brands: commit frequency, issue closing, release frequency).

**Disallowed**:
- Historical activity only (last update > 1 year ago, "archived but once vibrant").
- Marketing/vanity activity (high frequency of low-substance posts; "inactivity masquerading as activity").
- Empty-text changelog URLs (no substance, just links).
- Social media follower counts or engagement metrics alone (this is presencia, not vitalidad).

#### Thin Requirements

Vitalidad is **thin** when:

- Recent activity exists (≤ 60 days) but is inconsistent (months of silence between posts).
- Evidence of activity is all external (press mentions) with no owned surface updates.
- Activity is high-frequency but low-substance (daily social posts with no feature substance).

#### Blocked

Vitalidad is **blocked** when:

- Last activity > 1 year ago.
- No evidence of evolution or updates.
- Web presence exists but appears frozen (same content from 2 years ago, no changelog, no new posts).

#### Can Score with Zero Evidence?

**No.** Zero vitalidad evidence → abstain. Dimension is skipped.

However, brands with minimal public activity (some B2B enterprise software, closed-door products) may have zero public vitalidad evidence but be actively developed internally. This is a confound; recommend manual review or Deep Research if vitalidad is critical to decision.

#### Minimum Externality

**Minimum 20% external recommended** (press mentions, external tracking like Releasebot).

Pure owned activity (changelog + blog) is sufficient for ready status. External corroboration strengthens confidence.

#### What Collection Must Provide

- Owned surface recency (last update date, change detection).
- Changelog or version history (owned source).
- Social media activity (official accounts only).
- External press/news mentions (funding, launches, hiring).
- Temporal metadata (dates, not just presence).

#### What Evidence Packet v0 Must Validate

- ✓ Activity is recent (≤ 60 days for owned, ≤ 180 days for external press).
- ✓ Changelog URLs have text content (not empty-text URLs).
- ✓ Social profiles are verified as official (not ambiguous same-name profiles).
- ✓ Evolution is evident (not just repeated posts, but actual feature/version changes).
- ✓ Minimum 20% external evidence for high confidence.

---

## Cross-Dimension Patterns

### Dimensions That Can Operate on Owned Evidence Alone
- **Coherencia**: Yes. Intra-entity alignment doesn't require external validation.
- **Others**: No. Percepción requires external; diferenciacion requires comparative; vitalidad requires temporal activity signals (can be owned or external); presencia requires multi-channel (owned + external minimum).

### Dimensions That Fail Most Often in Evidence Packet v0

From the test data:

| Dimension | Vercel | LaunchDarkly | Builtwith/Kit | Watermelon | Pattern |
|---|---|---|---|---|---|
| Coherencia | 14% | 0% | 0% | 9% | Blocked by visual-only signals, technical artifacts |
| Diferenciacion | 0% | 0% | 0% | 0% | **No input has comparative evidence** |
| Percepcion | 100% | 100% | 0% | 25% | Depends on external discovery quality |
| Presencia | 27% | 27% | 0% | 10% | Depends on owned domain + channel verification |
| Vitalidad | 100% | 100% | 0% | 0% | Depends on changelog and activity recency |

**Key finding**: Diferenciación fails universally because no input snapshot includes competitor corpus evidence.

---

## Scoring Readiness Matrix

For each dimension, Evidence Packet v0 should output:

```json
{
  "dimension": "diferenciacion",
  "status": "ready | thin | blocked | insufficient_input",
  "evidence_count": {
    "eligible": 0,
    "review_gated": 2,
    "blocked": 2,
    "total": 4
  },
  "reason": "No comparative evidence or category-distinctive external language found. Owned claims only.",
  "recommendation": "Acquire competitor corpus or recommend manual review."
}
```

---

## Abstention Criteria

A dimension should **abstain from scoring** (not render a number, not render "unavailable") when:

- **Evidence count for ready status is 0 AND**
- **No meaningful thin evidence exists to suggest low score is justified.**

Abstention prevents nonsense like "diferenciacion: 0" which implies active but undifferentiated rather than "we don't have enough data."

---

## Recommended Next Steps

1. **Update Evidence Packet v0** to enforce these contracts per dimension.
2. **Add dimension coverage checks**: Each dimension outputs status (ready/thin/blocked/abstain).
3. **Test against all 4 cases**: Verify that Vercel and LaunchDarkly pass; Builtwith/Kit and Watermelon either pass or clearly show gaps.
4. **Identify acquisition gaps**: Note which dimensions require additional input (e.g., competitor corpus for diferenciacion).
5. **Before prompt integration**: Ensure that blocked/abstain dimensions do not render scores or findings.

