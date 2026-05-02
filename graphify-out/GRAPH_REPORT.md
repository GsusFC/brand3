# Graph Report - .  (2026-05-02)

## Corpus Check
- 126 files · ~93,384 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1884 nodes · 4611 edges · 34 communities detected
- Extraction: 61% EXTRACTED · 39% INFERRED · 0% AMBIGUOUS · INFERRED: 1779 edges (avg confidence: 0.64)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Collectors & Feature Extractors Tests|Collectors & Feature Extractors Tests]]
- [[_COMMUNITY_API Layer & SQLite Storage|API Layer & SQLite Storage]]
- [[_COMMUNITY_Report Derivation & Trust|Report Derivation & Trust]]
- [[_COMMUNITY_Feature Pipeline (Coherencia, Diferenciacion, Visual)|Feature Pipeline (Coherencia, Diferenciacion, Visual)]]
- [[_COMMUNITY_LLM Narrative Analysis|LLM Narrative Analysis]]
- [[_COMMUNITY_Web App Workers & Rate Limiting|Web App Workers & Rate Limiting]]
- [[_COMMUNITY_Design System & Deploy Docs|Design System & Deploy Docs]]
- [[_COMMUNITY_Brand Service & Dimension Confidence|Brand Service & Dimension Confidence]]
- [[_COMMUNITY_Documentation & Review Reports|Documentation & Review Reports]]
- [[_COMMUNITY_CLI Main Entry|CLI Main Entry]]
- [[_COMMUNITY_HTML Report Renderer|HTML Report Renderer]]
- [[_COMMUNITY_Context Collector|Context Collector]]
- [[_COMMUNITY_Online Presence Inventory|Online Presence Inventory]]
- [[_COMMUNITY_Web Tests (rate-limit, listings)|Web Tests (rate-limit, listings)]]
- [[_COMMUNITY_Report Readiness|Report Readiness]]
- [[_COMMUNITY_Web Collector (Firecrawl)|Web Collector (Firecrawl)]]
- [[_COMMUNITY_Niche Classifier|Niche Classifier]]
- [[_COMMUNITY_URL Validator|URL Validator]]
- [[_COMMUNITY_Vitalidad Tests|Vitalidad Tests]]
- [[_COMMUNITY_Editorial Policy|Editorial Policy]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]

## God Nodes (most connected - your core abstractions)
1. `SQLiteStore` - 206 edges
2. `WebData` - 140 edges
3. `ExaData` - 135 edges
4. `FeatureValue` - 107 edges
5. `ExaResult` - 92 edges
6. `LLMAnalyzer` - 90 edges
7. `WebCollector` - 85 edges
8. `ExaCollector` - 59 edges
9. `ContextData` - 59 edges
10. `ReportRenderer` - 54 edges

## Surprising Connections (you probably didn't know these)
- `Archive refactor notes 2026-04` --semantically_similar_to--> `Review Report — Dimensión Percepción`  [INFERRED] [semantically similar]
  docs/archive/refactor-notes-2026-04.md → REVIEW_REPORT.md
- `Diferenciación (5 dimensions)` --semantically_similar_to--> `Diferenciación dimension`  [INFERRED] [semantically similar]
  README.md → REVIEW_REPORT.md
- `BRAND3_LLM_API_KEY` --semantically_similar_to--> `LLMAnalyzer`  [INFERRED] [semantically similar]
  DEPLOY.md → REVIEW_REPORT.md
- `llm_analyzer.py LLMAnalyzer` --semantically_similar_to--> `LLMAnalyzer`  [INFERRED] [semantically similar]
  docs/scoring_review.md → REVIEW_REPORT.md
- `dimensions.py` --semantically_similar_to--> `dimensions.py module`  [INFERRED] [semantically similar]
  docs/scoring_review.md → REVIEW_REPORT.md

## Hyperedges (group relationships)
- **Brand3 Scoring Engine — 5 Dimensions** — readme_dimension_coherencia, readme_dimension_presencia, readme_dimension_percepcion, readme_dimension_diferenciacion, readme_dimension_vitalidad, engine_dimensions [EXTRACTED 1.00]
- **InsForge V1 Migration Stack** — insforge_v1_doc, insforge_v1_sql_file, handoff_doc, design_phase_frontend_3, insforge_concept_analysis, sqlite_store_sqlitestore [EXTRACTED 0.90]
- **Editorial Readiness — Modes and Dimension States** — editorial_readiness_doc, editorial_mode_publishable, editorial_mode_technical, editorial_mode_insufficient, editorial_state_ready, editorial_state_observation_only, editorial_state_technical_only, editorial_state_not_evaluable [EXTRACTED 1.00]

## Communities

### Community 0 - "Collectors & Feature Extractors Tests"
Cohesion: 0.03
Nodes (136): Test social profile detection from content., Test follower count extraction., Test data class creation., Test profile URL generation., test_data_classes(), test_follower_extraction(), test_profile_detection(), test_search_profiles() (+128 more)

### Community 1 - "API Layer & SQLite Storage"
Cohesion: 0.02
Nodes (60): AnalysisJobResponse, AnalyzeRequest, AnalyzeResponse, GateConfigRequest, PromoteBaselineRequest, FastAPI app exposing Brand3 Scoring as a web backend., RollbackResponse, BaseModel (+52 more)

### Community 2 - "Report Derivation & Trust"
Cohesion: 0.02
Nodes (97): build_trust_summary(), dimension_status_counts_from_confidence(), dimension_status_counts_from_report_dimensions(), _empty_counts(), limited_dimensions_from_confidence(), limited_dimensions_from_report_dimensions(), quality_label(), Shared trust status helpers for API and reports. (+89 more)

### Community 3 - "Feature Pipeline (Coherencia, Diferenciacion, Visual)"
Cohesion: 0.03
Nodes (80): Cheap context-readiness collector.  This module performs a low-cost pre-scan usi, _domain_anchor(), Exa collector for semantic search, competitor discovery, and AI visibility.  Use, Web collector using Firecrawl.  Scrapes the brand's website and extracts: - HTML, AuthenticityAnalyzer, AuthenticityResult, Brand Authenticity Analyzer.  Detects whether a brand feels REAL vs AI-generated, Run full authenticity analysis. (+72 more)

### Community 4 - "LLM Narrative Analysis"
Cohesion: 0.04
Nodes (76): LLMAnalyzer, Make an LLM call via the OpenAI-compatible endpoint.          Default `max_token, Make an LLM call expecting strict JSON response.          Uses `response_format=, What category/positioning does the brand claim?         Returns: {category, valu, Is the brand saying something DIFFERENT from competitors?         Returns: {uniq, LLM judgment for positioning clarity with literal evidence., LLM judgment for brand uniqueness vs generic language., Analyze sentiment from third-party mentions.         Returns: {overall_sentiment (+68 more)

### Community 5 - "Web App Workers & Rate Limiting"
Cohesion: 0.03
Nodes (74): BaseSettings, get_client_ip(), rate_limit_middleware(), Per-IP rate limit for POST /analyze.  Counts are persisted in `web_requests` — s, Resolve the requester IP, honouring X-Forwarded-For in production., create_serializer(), is_team_request(), Signed cookie that bypasses the per-IP rate limit for the FLOC team. (+66 more)

### Community 6 - "Design System & Deploy Docs"
Cohesion: 0.02
Nodes (107): Canonical benchmark, Exploratory benchmark, Benchmark Policy doc, base profile, enterprise_ai profile, frontier_ai profile, physical_ai profile, examples/canonical_benchmark.template.json (+99 more)

### Community 7 - "Brand Service & Dimension Confidence"
Cohesion: 0.04
Nodes (99): list_calibration_profiles(), _as_float(), _context_summary_from_snapshot(), dimension_confidence_from_features(), dimension_confidence_from_records(), dimension_confidence_from_snapshot(), _has_feature_evidence(), _parse_raw() (+91 more)

### Community 8 - "Documentation & Review Reports"
Cohesion: 0.03
Nodes (90): learning/applier.py, BrandService, learning/calibration.py, CoherenciaExtractor, BRAND3_LLM_API_KEY, _clean_string_list helper, _competitor_distance method, _positioning_clarity method (+82 more)

### Community 9 - "CLI Main Entry"
Cohesion: 0.05
Nodes (80): add_feedback(), _add_int_ids(), apply_candidates(), benchmark_profiles(), brand_report(), _brand_service(), _build_parser(), _build_run_audit_context() (+72 more)

### Community 10 - "HTML Report Renderer"
Cohesion: 0.06
Nodes (36): _cmd_render_report(), _render_report_with_readiness_diagnostic(), slugify(), HTML report generation for Brand3 analysis runs., _chip_label(), Render a Brand3 run snapshot into a self-contained HTML report.  Single-file out, Pull run_id snapshot from SQLite and write HTML. Returns the output path., Render the most recent run. Raises if the store is empty. (+28 more)

### Community 11 - "Context Collector"
Cohesion: 0.06
Nodes (34): ContextCollector, Collects machine-readability signals without paid APIs., build_parser(), capture_confidence(), CaptureRow, classify_surface(), cmd_capture_benchmark(), cmd_capture_probe() (+26 more)

### Community 12 - "Online Presence Inventory"
Cohesion: 0.08
Nodes (40): build_parser(), build_single_parser(), classify_page(), _collect_direct_candidate(), collect_inventory(), _collect_primary(), _collection_method_from_web_data(), common_path_candidates() (+32 more)

### Community 13 - "Web Tests (rate-limit, listings)"
Cohesion: 0.05
Nodes (22): _install_env(), RateLimitTests, Rate-limit middleware — counter, window, and team bypass., No-op helper — kept for readability in the window test., sys_module_keys(), _install_env(), End-to-end web flow: /analyze → queue → /r/{token}/status → /r/{token}., WebAppFlowTests (+14 more)

### Community 14 - "Report Readiness"
Cohesion: 0.18
Nodes (20): _as_float(), _dimension_evidence_count(), _dimension_narrative_state(), _dimension_score(), _dimension_state(), evaluate_report_readiness(), _fallback_detected_by_dimension(), _feature_record_looks_fallback() (+12 more)

### Community 15 - "Web Collector (Firecrawl)"
Cohesion: 0.08
Nodes (10): Scrape URL via Firecrawl Python SDK. Returns legacy {content, raw, error} shape., Remove obvious cookie/consent UI sludge from scraped markdown., Drop leading UI/navigation sludge before the first meaningful content block., Extract a meaningful title from cleaned markdown., Drop any leading content that appears before the extracted title., Fetch raw HTML directly when Firecrawl returns no useful markdown., Render a page in Chromium when static fetches cannot see useful text., Extract a minimal, readable text snapshot from raw HTML. (+2 more)

### Community 16 - "Niche Classifier"
Cohesion: 0.13
Nodes (14): classify_brand_niche(), _early_signal_text(), _has_primary_source_evidence(), _has_required_subtype_evidence(), _normalise_text(), Heuristic niche classifier for brand calibration profiles., Keep classification anchored to title/hero copy instead of long-body noise., _score_keywords() (+6 more)

### Community 17 - "URL Validator"
Cohesion: 0.13
Nodes (15): URL validator — accepts valid public URLs, rejects private/unsafe ones., Short-circuit getaddrinfo so tests don't need network., _skip_dns(), test_accepts_http_with_path(), test_accepts_https_root(), test_blocklist_env_var(), test_normalizes_host_and_trailing_slash(), UrlValidatorTests (+7 more)

### Community 18 - "Vitalidad Tests"
Cohesion: 0.18
Nodes (1): VitalidadExtractorTests

### Community 19 - "Editorial Policy"
Cohesion: 0.24
Nodes (9): _editorial_policy_from_readiness(), allowed_language_for_dimension_state(), evidence_language_hint(), label_dimension_state(), label_report_mode(), Editorial language policy helpers for report readiness.  These functions are pur, tone_for_dimension_state(), tone_for_report_mode() (+1 more)

### Community 20 - "Community 20"
Cohesion: 0.43
Nodes (7): _brand_name(), _format_value(), inspect_path(), _load_build_report_context(), _load_reports_submodule_without_package_init(), main(), print_result()

### Community 21 - "Community 21"
Cohesion: 0.67
Nodes (1): Shared pytest setup for the Brand3 test suite.  Isolates unit tests from any rea

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Brand3 web application — FastAPI front-end for the scoring engine.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Middleware and auth helpers for the web app.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Background workers and helpers for processing analysis requests.

### Community 26 - "Community 26"
Cohesion: 2.0
Nodes (1): HTTP routes for the Brand3 web app.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Configuration for Brand3 Scoring.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Quality helpers for confidence and coverage metadata.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Learning utilities for Brand3 Scoring.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Storage helpers for Brand3 Scoring.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): API package for Brand3 Scoring.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Service layer for Brand3 Scoring.

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): AuthenticityAnalyzer

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): percepcion_llm.py (legacy)

## Ambiguous Edges - Review These
- `uniqueness feature` → `learning/calibration.py`  [AMBIGUOUS]
  REVIEW_REPORT.md · relation: references

## Knowledge Gaps
- **237 isolated node(s):** `Web app settings loaded from env vars / .env.`, `Brand3 web application — FastAPI front-end for the scoring engine.`, `Small view helpers shared across web routes (bands, bars, formatting).`, `Add `band`, `band_letter`, `bar`, `score_display` fields for templates.`, `Shared Jinja2 template environment for the web app.` (+232 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Vitalidad Tests`** (22 nodes): `VitalidadExtractorTests`, `._exa_with_dates()`, `._make_momentum_llm()`, `.setUp()`, `.test_content_recency_30_days_is_mid_high()`, `.test_content_recency_6_months_drops_to_mid()`, `.test_content_recency_no_dates_returns_neutral_with_reason()`, `.test_content_recency_over_365_days_is_very_low()`, `.test_content_recency_past_year_is_low()`, `.test_content_recency_recent_publication_scores_high()`, `.test_extract_always_returns_three_features()`, `.test_momentum_with_all_evidence_items_malformed_flags_partial()`, `.test_momentum_with_invalid_verdict_falls_back()`, `.test_momentum_with_llm_uses_structured_verdict()`, `.test_momentum_with_malformed_evidence_items_are_filtered()`, `.test_momentum_with_no_recent_mentions_returns_fallback()`, `.test_momentum_with_non_list_evidence_degrades_confidence()`, `.test_momentum_with_unclear_verdict_has_lower_confidence()`, `.test_momentum_without_llm_returns_heuristic_fallback()`, `.test_publication_cadence_fewer_than_2_dates_is_low()`, `.test_publication_cadence_moderate_rhythm_scores_mid()`, `.test_publication_cadence_regular_rhythm_scores_high()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (3 nodes): `_disable_real_llm_default()`, `conftest.py`, `Shared pytest setup for the Brand3 test suite.  Isolates unit tests from any rea`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (2 nodes): `__init__.py`, `Brand3 web application — FastAPI front-end for the scoring engine.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (2 nodes): `Middleware and auth helpers for the web app.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (2 nodes): `__init__.py`, `Background workers and helpers for processing analysis requests.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (2 nodes): `HTTP routes for the Brand3 web app.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (2 nodes): `config.py`, `Configuration for Brand3 Scoring.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (2 nodes): `Quality helpers for confidence and coverage metadata.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (2 nodes): `Learning utilities for Brand3 Scoring.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (2 nodes): `__init__.py`, `Storage helpers for Brand3 Scoring.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (2 nodes): `API package for Brand3 Scoring.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (2 nodes): `Service layer for Brand3 Scoring.`, `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `AuthenticityAnalyzer`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `percepcion_llm.py (legacy)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `uniqueness feature` and `learning/calibration.py`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `SQLiteStore` connect `API Layer & SQLite Storage` to `Collectors & Feature Extractors Tests`, `Feature Pipeline (Coherencia, Diferenciacion, Visual)`, `LLM Narrative Analysis`, `Web App Workers & Rate Limiting`, `Brand Service & Dimension Confidence`, `CLI Main Entry`, `HTML Report Renderer`?**
  _High betweenness centrality (0.390) - this node is a cross-community bridge._
- **Why does `LLMAnalyzer` connect `LLM Narrative Analysis` to `Collectors & Feature Extractors Tests`, `API Layer & SQLite Storage`, `Feature Pipeline (Coherencia, Diferenciacion, Visual)`, `Brand Service & Dimension Confidence`, `HTML Report Renderer`, `Vitalidad Tests`?**
  _High betweenness centrality (0.166) - this node is a cross-community bridge._
- **Why does `run()` connect `Brand Service & Dimension Confidence` to `Collectors & Feature Extractors Tests`, `API Layer & SQLite Storage`, `Report Derivation & Trust`, `Feature Pipeline (Coherencia, Diferenciacion, Visual)`, `LLM Narrative Analysis`, `Context Collector`, `Niche Classifier`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Are the 148 inferred relationships involving `SQLiteStore` (e.g. with `Brand3 Scoring — CLI entry point.  The reusable implementation lives in `src.ser` and `Shim legacy URL-as-first-arg form into `analyze <url> [...]`.`) actually correct?**
  _`SQLiteStore` has 148 INFERRED edges - model-reasoned connections that need verification._
- **Are the 136 inferred relationships involving `WebData` (e.g. with `PercepcionExtractorTests` and `DiferenciacionExtractorTests`) actually correct?**
  _`WebData` has 136 INFERRED edges - model-reasoned connections that need verification._
- **Are the 132 inferred relationships involving `ExaData` (e.g. with `PercepcionExtractorTests` and `DiferenciacionExtractorTests`) actually correct?**
  _`ExaData` has 132 INFERRED edges - model-reasoned connections that need verification._