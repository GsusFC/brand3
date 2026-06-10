# Brand3 Observed Related Surfaces Input Contract

Date: 2026-05-17

Scope: input-contract memo only. No builder code, runtime integration, prompts, scoring, rendering, payload format, Visual Signature code, LLM calls, report audits, or entity-state fixtures were changed.

## Purpose

`entity_resolution.related_surfaces` is now the canonical upstream source for related-surface metadata. `observed_related_surfaces` remains a compatibility shape for older fixtures and docs, but new upstream producers should emit the packet field.

The builder v0 correctly left `observed_related_surfaces` empty for all generated outputs when the current machine-readable inputs did not provide safe related-surface metadata. That was conservative and correct.

The next step is not to let the builder infer related surfaces from arbitrary URLs. The next step is to expose a narrowly defined input field that separates:

- verified or plausible related surfaces,
- adjacent but uncertain surfaces,
- ambiguous name matches,
- unrelated evidence URLs.

## Definition

An observed related surface is a domain, subdomain, product page, developer surface, social/account surface, repository, marketplace profile, or adjacent owned/near-owned property that appears relevant to the audited entity and is supported by explicit evidence.

It is not automatically an alias.

It is not automatically owned by the brand.

It is not automatically part of the audited entity.

It is a candidate surface for entity-level composition review.

## What Counts

A surface may count when at least one of these conditions is true.

### Explicit discovery/entity metadata

The surface is emitted by a discovery or entity metadata layer as related to the audited entity.

Acceptable examples:

- canonical domain,
- product domain,
- parent brand domain,
- developer documentation domain,
- marketplace profile tied to the audited product,
- official repository tied to the audited product,
- verified social profile,
- known parent/sub-brand surface.

Required metadata:

- relation type,
- evidence URL or evidence object,
- confidence,
- source.

### Manually reviewed related surface

The surface is manually reviewed and marked as relevant for the case.

Acceptable examples:

- `watermelon.ai` reviewed as adjacent to `watermelon.sh`,
- `developer.watermelon.ai` reviewed as a developer surface,
- `heyiris.ai` reviewed as potentially adjacent but not confirmed,
- `builtwith.com` reviewed as an adjacent entity surface for a Builtwith/Kit case.

Manual review must not remove uncertainty. It should usually keep `requires_human_review: true` unless ownership/relation is explicit.

### Deterministic same-root/subdomain relationship

The surface shares a deterministic same-root relationship with the audited URL.

Safe examples:

- `docs.example.com` for `example.com`,
- `developer.example.com` for `example.com`,
- `app.example.com` for `example.com`,
- `kb.example.com` for `example.com`.

This can be high-confidence only when the root domain is the same and the surface is not a public-hosting or generic platform domain.

### Explicit product or developer surface

The surface is clearly a product/developer/documentation surface and the evidence links it to the audited entity.

Examples:

- `developer.watermelon.ai`,
- `github.com/watermelontools` only if discovery evidence ties it to Watermelon,
- Product Hunt page only if it is explicitly for the audited product.

These should usually remain medium or low confidence unless verified by owned metadata.

## What Must Not Count

These must not be added to `observed_related_surfaces` by default.

### Arbitrary evidence URLs

A URL used as evidence is not necessarily a related surface.

Examples:

- a news article,
- competitor page,
- review site,
- directory listing,
- analyst article,
- unrelated GitHub search result,
- random Product Hunt result,
- SEO page mentioning the same word.

Evidence URLs support findings. They do not automatically define entity surfaces.

### Name similarity alone

Shared words are not enough.

Examples:

- `watermelon.co` is not related to `watermelon.sh` just because both contain Watermelon.
- an Iris AI domain is not related to Iris Design just because both contain Iris.
- a honey watermelons brand-refresh article is not a Watermelon product surface.

### Third-party mentions

Mentioning the brand or product does not make the source a related surface.

Examples:

- a press article,
- a review,
- a competitor comparison,
- a news listing,
- a search result excerpt.

### Search result co-occurrence

If the surface appears near the brand in search results, that is discovery context, not entity relation.

Search co-occurrence can create a candidate for review, but the relation confidence should be low and `requires_human_review` must be true.

### Visual or stylistic similarity

Visual similarity must not create related-surface metadata.

Visual/perceptual confidence is not evidentiary confidence.

## Allowed Sources

### `entity_discovery`

Use when the entity discovery layer emits explicit canonical, parent, product, or related domain fields.

Allowed source value:

```json
"entity_discovery"
```

### `manual_review`

Use for surfaces curated during offline review or memo work.

Allowed source value:

```json
"manual_review"
```

### `deterministic_domain_rule`

Use for same-root/subdomain relationships.

Allowed source value:

```json
"deterministic_domain_rule"
```

### Future explicit discovery metadata

Brand3 may later expose a dedicated list from discovery enrichment. If it does, that list should still use the same object shape and confidence/review rules.

### Canonical packet source

New upstream producers should prefer `entity_resolution.related_surfaces` in the Evidence Packet / entity-resolution layer. Consumers may keep accepting `observed_related_surfaces` as a legacy compatibility alias, but they should not treat it as the preferred source of truth.

The live Iris and Watermelon fixtures under `examples/reports/narrative_harness/entity_state/inputs/` have already been migrated to the packet field. Any remaining `observed_related_surfaces` examples in this repository are historical or compatibility-only.

## Disallowed Sources

Do not populate `observed_related_surfaces` from:

- arbitrary evidence URLs,
- name similarity alone,
- third-party mentions,
- search result co-occurrence,
- visual similarity,
- score differences,
- LLM assumptions,
- report prose speculation.

## Suggested Shape

The recommended input shape is:

```json
{
  "observed_related_surfaces": [
    {
      "surface": "watermelon.ai",
      "relation_type": "adjacent_domain",
      "evidence": ["https://watermelon.ai"],
      "confidence": "medium",
      "requires_human_review": true,
      "source": "manual_review"
    }
  ]
}
```

## Field Semantics

### `surface`

Required.

The normalized domain, subdomain, repository path, marketplace path, social/account path, or product URL.

Examples:

- `watermelon.ai`
- `developer.watermelon.ai`
- `github.com/watermelontools`
- `producthunt.com/products/watermelon`
- `builtwith.com`

### `relation_type`

Required.

Allowed values:

- `canonical_domain`
- `same_root_subdomain`
- `adjacent_domain`
- `product_surface`
- `developer_surface`
- `documentation_surface`
- `repository_surface`
- `marketplace_profile`
- `social_profile`
- `parent_surface`
- `sub_brand_surface`
- `ambiguous_name_match`

`ambiguous_name_match` must always have low confidence and `requires_human_review: true`.

### `evidence`

Required.

An array of URLs, evidence IDs, or source references supporting why this surface is included.

This should be evidence of relation, not merely evidence of existence.

Weak:

```text
surface appeared in search results
```

Better:

```text
owned page links to this developer surface
```

### `confidence`

Required.

Allowed values:

- `high`
- `medium`
- `low`

Guidelines:

- `high`: same-root/subdomain or explicit owned/entity metadata.
- `medium`: manually reviewed adjacent or product/developer surface with supporting evidence.
- `low`: ambiguous name match, weak external association, or search-discovered candidate requiring review.

### `requires_human_review`

Required.

Use `true` unless the relationship is deterministic same-root/subdomain or explicit in trusted entity metadata.

### `source`

Required.

Allowed values:

- `entity_discovery`
- `manual_review`
- `deterministic_domain_rule`

Future explicit sources may be added only if they preserve the same confidence and review semantics.

## Relation Type Examples

### Watermelon

Safe or plausible candidates:

```json
{
  "observed_related_surfaces": [
    {
      "surface": "watermelon.ai",
      "relation_type": "adjacent_domain",
      "evidence": ["manual Phase 2 review identified it as an adjacent Watermelon surface"],
      "confidence": "medium",
      "requires_human_review": true,
      "source": "manual_review"
    },
    {
      "surface": "developer.watermelon.ai",
      "relation_type": "developer_surface",
      "evidence": ["manual Phase 2 review identified it as a developer surface"],
      "confidence": "medium",
      "requires_human_review": true,
      "source": "manual_review"
    },
    {
      "surface": "github.com/watermelontools",
      "relation_type": "repository_surface",
      "evidence": ["manual Phase 2 review identified it as a possible repository surface"],
      "confidence": "low",
      "requires_human_review": true,
      "source": "manual_review"
    }
  ]
}
```

Do not include by default:

- `drinkwtrmln.com`
- unrelated honey watermelons articles,
- arbitrary Watermelon-name domains without relation evidence.

Those may be captured elsewhere as ambiguous search noise, not as related surfaces.

### Iris

Possible candidates:

```json
{
  "observed_related_surfaces": [
    {
      "surface": "irisdesign.in",
      "relation_type": "ambiguous_name_match",
      "evidence": ["manual Phase 2 review identified name-adjacent Iris design surface"],
      "confidence": "low",
      "requires_human_review": true,
      "source": "manual_review"
    },
    {
      "surface": "heyiris.ai",
      "relation_type": "ambiguous_name_match",
      "evidence": ["manual Phase 2 review identified AI-heavy Iris surface"],
      "confidence": "low",
      "requires_human_review": true,
      "source": "manual_review"
    }
  ]
}
```

Do not promote these to aliases or owned surfaces without explicit evidence.

### Builtwith / Kit

Possible candidates:

```json
{
  "observed_related_surfaces": [
    {
      "surface": "kit.com",
      "relation_type": "parent_surface",
      "evidence": ["manual review of builtwith.kit.com context"],
      "confidence": "medium",
      "requires_human_review": true,
      "source": "manual_review"
    },
    {
      "surface": "builtwith.com",
      "relation_type": "adjacent_domain",
      "evidence": ["manual review identified BuiltWith naming ambiguity"],
      "confidence": "low",
      "requires_human_review": true,
      "source": "manual_review"
    }
  ]
}
```

This preserves the distinction between observed relation pressure and verified equivalence.

## Builder Behavior

The offline `EntityNarrativeState` builder should:

- accept this field from snapshot/base dossier metadata,
- copy normalized surfaces into `state.entity_aliases.observed_related_surfaces`,
- set `needs_review: true` when any item requires review,
- preserve relation metadata when possible,
- avoid turning related surfaces into primary entity facts,
- avoid creating contradiction candidates from related surfaces alone.

The builder should not:

- infer surfaces from arbitrary evidence URLs,
- infer ownership,
- infer entity equivalence,
- use related surfaces to change scoring,
- use related surfaces to rewrite report prose,
- use related surfaces as Visual Signature input.

## Recommended Future Output Shape

Current builder output uses:

```json
"entity_aliases": {
  "primary": "watermelon.sh",
  "observed_related_surfaces": [],
  "needs_review": false,
  "confidence": "medium"
}
```

Future builder output may preserve richer metadata:

```json
"entity_aliases": {
  "primary": "watermelon.sh",
  "observed_related_surfaces": [
    {
      "surface": "watermelon.ai",
      "relation_type": "adjacent_domain",
      "confidence": "medium",
      "requires_human_review": true,
      "source": "manual_review"
    }
  ],
  "needs_review": true,
  "confidence": "medium"
}
```

This is still not an alias assertion. The field name remains historical from the current state shape, but the semantics should be:

```text
observed related surfaces, not verified aliases
```

## Implementation Readiness

This contract is ready to inform a small future builder update, but not runtime integration.

Before implementation, Brand3 should decide where the input field lives:

- snapshot metadata,
- base dossier metadata,
- entity discovery output,
- offline manual review artifact.

Recommended next step:

Create one small offline input fixture for Iris or Watermelon with manually reviewed `observed_related_surfaces`, then update the builder to pass through the structured list without inference.

## Non-Goals

Do not use this contract to:

- change scoring,
- change report prose,
- change prompts,
- change rendering,
- mutate persisted report payloads,
- integrate Visual Signature,
- perform automatic entity resolution,
- treat all discovered URLs as related surfaces.
