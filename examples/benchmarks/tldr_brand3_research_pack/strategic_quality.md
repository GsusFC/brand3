# TLDR Brand3 strategic quality evaluation

- Version: `tldr_brand3_strategic_quality_v0_1`
- Cases evaluated: `7`
- Total score: `91.1`

## Dimension Scores

| dimension             | score |
| --------------------- | ----- |
| audience              | 90.0  |
| differentiation       | 78.6  |
| entity_separation     | 100.0 |
| evidence_traceability | 100.0 |
| frictions             | 100.0 |
| offer                 | 80.7  |
| personality           | 85.7  |
| vision                | 93.6  |

## Case Summary

| case                                   | archetype                                   | score | failures | top failures                                                                                                                                                      |
| -------------------------------------- | ------------------------------------------- | ----- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| langchain-like                         | multiproduct_saas                           | 100.0 | 0        | —                                                                                                                                                                 |
| single-product-saas                    | single_product_saas                         | 100.0 | 0        | —                                                                                                                                                                 |
| retail                                 | ecommerce                                   | 100.0 | 0        | —                                                                                                                                                                 |
| product-subdomain                      | parent_brand_product_surface                | 100.0 | 0        | —                                                                                                                                                                 |
| base44-current-regression              | founder_proof_overpromotion                 | 83.1  | 4        | differentiation_missing_required_term: expected 'software creation becomes a conversation'; personality_contains_forbidden_term: found 'founder'                  |
| creatify-current-regression            | performance_marketing_proof_overcompression | 73.1  | 6        | offer_missing_required_term: expected 'AI ad platform'; offer_contains_forbidden_term: found 'cost reduction'                                                     |
| naturaumana-product-surface-regression | parent_brand_product_surface                | 81.2  | 4        | offer_missing_required_concept: expected one of ['Natura Umana', 'parent brand']; audience_missing_required_concept: expected one of ['people', 'users', 'teams'] |

## Failure Taxonomy

| taxonomy                                | count |
| --------------------------------------- | ----- |
| differentiation_missing_required_term   | 3     |
| personality_contains_forbidden_term     | 3     |
| offer_contains_forbidden_term           | 2     |
| audience_missing_required_concept       | 1     |
| audience_missing_required_term          | 1     |
| differentiation_contains_forbidden_term | 1     |
| offer_missing_required_concept          | 1     |
| offer_missing_required_term             | 1     |
| vision_contains_forbidden_term          | 1     |

## Recommendations

- Separate the core offer from proof metrics and preserve the expected offer category.
- Strengthen brand_idea checks so weak metaphors or generic product mechanics do not pass as differentiation.
- Keep founder, funding, and press context out of personality unless owned expression supports it.
- Downgrade vision when future language is over-broad or not directly supported by owned evidence.
