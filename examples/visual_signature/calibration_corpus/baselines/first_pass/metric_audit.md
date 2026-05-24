# Visual Signature Metric Audit

Calibration diagnostics only. This report does not affect scoring, rubric dimensions, reports, or UI.

- Rows: 139
- Strongest metrics: dom_viewport_agreement_score, dom_viewport_disagreement_severity_score, viewport_whitespace, typography_complexity, visible_cta_weight, density_agreement_score
- Weakest metrics: cta_density, vision_confidence, composition_agreement_score, composition_stability, structural_agreement_score, signal_availability
- Saturated metrics: composition_stability, structural_agreement_score, composition_agreement_score, cta_density, signal_availability
- Noisy metrics: composition_stability, structural_agreement_score, composition_agreement_score, palette_agreement_score, cta_density, component_density, signal_availability
- Category-sensitive metrics: viewport_whitespace, viewport_density_score, dom_viewport_agreement_score, dom_viewport_disagreement_severity_score, palette_agreement_score, visible_cta_weight, component_density, typography_complexity
- Category-insensitive metrics: composition_stability, structural_agreement_score, density_agreement_score, composition_agreement_score, cta_density, extraction_confidence, vision_confidence, signal_availability, signal_coverage

## Numeric Metrics

| Metric | Available | Median | P10 | P90 | IQR | Entropy | Saturated | Noise | Diagnostic |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: |
| component_density | 100% | 1.00 | 0.75 | 1.00 | 0.05 | 0.41 | False | medium | 0.82 |
| composition_agreement_score | 100% | 1.00 | 1.00 | 1.00 | 0.00 | 0.11 | True | medium | 0.39 |
| composition_stability | 100% | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | True | medium | 0.25 |
| cta_density | 100% | 1.00 | 0.75 | 1.00 | 0.00 | 0.32 | True | medium | 0.65 |
| density_agreement_score | 100% | 1.00 | 0.10 | 1.00 | 0.90 | 0.49 | False | low | 0.85 |
| dom_viewport_agreement_score | 100% | 0.50 | 0.00 | 1.00 | 1.00 | 0.99 | False | low | 1.00 |
| dom_viewport_disagreement_severity_score | 100% | 0.25 | 0.00 | 1.00 | 0.60 | 0.94 | False | low | 0.98 |
| extraction_confidence | 100% | 0.65 | 0.58 | 0.71 | 0.07 | 0.58 | False | low | 0.71 |
| palette_agreement_score | 100% | 1.00 | 0.55 | 1.00 | 0.45 | 0.99 | False | medium | 0.83 |
| palette_complexity | 100% | 0.79 | 0.58 | 0.90 | 0.18 | 0.80 | False | low | 0.84 |
| signal_availability | 100% | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | True | medium | 0.25 |
| signal_coverage | 100% | 0.69 | 0.60 | 0.77 | 0.09 | 0.66 | False | low | 0.70 |
| signal_usability | 100% | 0.52 | 0.39 | 0.65 | 0.14 | 0.74 | False | low | 0.78 |
| structural_agreement_score | 100% | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | True | medium | 0.25 |
| typography_complexity | 100% | 0.00 | 0.00 | 1.00 | 0.31 | 0.62 | False | low | 0.89 |
| viewport_density_score | 100% | 0.90 | 0.20 | 0.90 | 0.35 | 0.70 | False | low | 0.82 |
| viewport_whitespace | 100% | 0.28 | 0.01 | 0.90 | 0.57 | 0.93 | False | low | 0.98 |
| visible_cta_weight | 100% | 0.80 | 0.60 | 1.00 | 0.10 | 0.51 | False | low | 0.85 |
| vision_confidence | 100% | 0.85 | 0.77 | 0.89 | 0.05 | 0.42 | False | low | 0.63 |

## Categorical Metrics

| Metric | Entropy | Top value | Distribution |
| --- | ---: | --- | --- |
| dom_viewport_agreement_level | 0.99 | high | high:57, low:43, medium:39 |
| dom_viewport_disagreement_severity | 0.94 | none | major:23, minor:39, moderate:20, none:57 |
| viewport_composition | 0.61 | dense_grid | balanced_blocks:17, blank:4, dense_grid:101, sparse_single_focus:17 |
| viewport_density | 0.70 | dense | balanced:17, dense:101, sparse:21 |
| viewport_whitespace_band | 0.91 | low | high:18, low:65, moderate:24, very_high:32 |
