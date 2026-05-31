<claude-mem-context>
# Memory Context

# [brand3] recent context, 2026-05-30 9:45am GMT+2

Legend: 🎯session 🔴bugfix 🟣feature 🔄refactor ✅change 🔵discovery ⚖️decision 🚨security_alert 🔐security_note
Format: ID TIME TYPE TITLE
Fetch details: get_observations([IDs]) | Search: mem-search skill

Stats: 50 obs (19,315t read) | 212,283t work | 91% savings

### May 20, 2026
S335 Create TL;DR brand block interpreter specs documentation for Brand3 methodology (May 20 at 8:22 PM)
### May 22, 2026
S337 Investigación de consistencia de datos entre Magnetism Scanner y Brand Audit — ¿usan todos la misma información? (May 22 at 4:25 PM)
S341 Feed proof pages into brand3 strategic evidence packet — expand proof_points evidence extraction from owned web subpages, testimonials, and customer content (May 22 at 4:41 PM)
### May 25, 2026
S342 Remove scanner limitation — fix bug where `attributes` dimension was incorrectly returning `absent` despite available evidence (May 25 at 9:55 PM)
### May 26, 2026
S346 Brand3 Block Interpreter Architecture — design discussion + /review on current changes (May 26 at 10:29 AM)
### May 27, 2026
S347 Fly.io deploy failing due to placeholder token — fix FLY_API_TOKEN authentication (May 27 at 6:20 PM)
S348 Create a detailed operational report documenting everything the Brand3 app does, including questions it answers and example expected outputs (May 27 at 8:43 PM)
### May 28, 2026
S349 Brand3 Lab deprecation decision — which components to absorb into Brand Audit and Magnetism Scanner vs. delete (May 28 at 7:06 AM)
S350 Continue (sigamos) — mapping new architecture after major brand3 cleanup to ensure strategist pass compiles and tests pass (May 28 at 7:47 AM)
### May 29, 2026
S351 Implement Analyst Pass: LLM-driven TLDR Brand3 generation from Research Pack, including post-LLM guardrails, normalizer, extractor integration, and full test suite (May 29 at 9:17 AM)
### May 30, 2026
5425 8:40a 🟣 BRAND3_MAGNETISM_RESEARCH_PACK_TLDR Analyst Pass Validated in Local A/B Test
5428 " 🔵 Analyst Pass Failing Due to Gemini Returning JSON Array Instead of Object
5429 " 🔴 _coerce_analyst_raw_json Added to Handle Gemini List-Wrapped JSON Response
5430 8:41a 🟣 test_single_item_array_response_is_accepted Added to Cover Gemini JSON Array Drift
5431 " 🔵 Full Research Pack + Analyst Pass Pipeline Validated End-to-End on LangChain (run #154)
5432 " 🔵 run_web_dev_macos.sh Requires OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES for LLM Timeout Enforcement
5433 8:42a 🔵 Magnetism Scan #48 (LangChain) Accessible via Web UI at /magnetism-scanner/scan/48
5434 8:43a 🔵 Scan #48 Web UI Shows Analyst Pass TLDR Content; Mode Label Not Exposed to End Users
5435 " 🔵 runs Table Has No raw_inputs Column; Use SQLiteStore.get_run_snapshot() Instead
5436 " 🔵 LangChain Entity Discovery: 3 Product Surfaces, 17 Owned Surfaces, No Parent Brand
5437 " ✅ Research Pack + Analyst Pass Feature Branch: 542 Insertions Across 15 Files, Not Yet Committed
5438 9:01a 🔵 Brand3 Research Pipeline: Entity Scope and Offer Extraction Architecture
5439 9:02a 🔵 EvidenceGraph → BrandResearchPack Bridge: Full Implementation Detail
5440 " 🔵 Test Snapshot Fixtures for Evidence Graph Pipeline
5441 " 🟣 Company-Brand Offer Extraction: Entity-Aware Scoring and Candidate Filtering
5442 " 🟣 LangChain-Like Multi-Product Test Fixture Added to Evidence Graph Test Suite
5443 9:03a 🔵 product_summary Falls Back to Company-Level Offer Due to Product Claims Being Typed as "audience"
5444 " 🔴 Fixed: _product_summary_text() Now Finds Product-Scoped "audience" and "hero_claim" Claims
5445 " ✅ Full Test Suite Green: 89 Tests Pass After Company-Brand Offer Extraction Improvements
5446 " 🔵 Live LangChain Scan (ID 154) Validates Company-Brand Offer Extraction on Real Data
5447 9:04a 🔵 LangChain Live Scan: /about Page Generates Multiple Claim Types from Same Source URL
5448 " 🔴 Penalize Heading-Prefixed and Truncated Summary Claims in Offer Scoring
5449 " 🔴 LangChain Scan 154: Offer Now Extracts Clean Distilled Sentence Instead of Heading-Prefixed Page Title
5450 9:06a ✅ Full End-to-End LangChain Rescan Triggered via run_magnetism_from_audit_run(154) with LLM
5451 " 🟣 End-to-End LangChain Rescan (Scan 50) Confirms Graph Pack Pipeline Produces Clean LLM TLDR Output
5452 " 🟣 Scan 50 Verified in Browser: LangChain Company Offer Displays Correctly in Magnetism Scanner UI
5453 9:07a 🔵 Working Tree State: New EvidenceGraph Research Pipeline Entirely Untracked, Plus 11 Modified Files
5454 9:25a ⚖️ Magnetism Scanner: Three-Page Structure Planned
5455 9:28a 🟣 Magnetism Scanner Three-Page Implementation Plan Active
5456 " 🔵 Magnetism Scanner Codebase Structure Mapped
5457 9:29a 🔵 Magnetism Detail Template: Current Single-Page Structure with Collapsible Methodology
5458 " 🔵 No Existing Tab CSS Pattern; Existing Tests Assert Page-Level Text Presence
5459 " 🔵 Reusable .vs-nav / .vs-nav-link CSS Pattern Available for Scanner Tabs
5460 9:30a 🟣 Magnetism Scanner Routes Refactored for Three-Tab Architecture
5461 " 🟣 Research Evidence Model: Fallback Surface Detection from Source Map
5462 " 🟣 Shared Tab Navigation Partial: magnetism_scan_nav.html.j2
5463 9:31a 🟣 magnetism_detail.html.j2: Nav Replaced with Partial, Methodology Section Removed
5464 9:32a 🟣 New Template: magnetism_research.html.j2 — Research Evidence Tab
5465 9:33a 🟣 New Template: magnetism_methodology.html.j2 — Methodology Details Tab
5466 " 🟣 Three-Tab Magnetism Scanner: All 33 Tests Pass
5467 " 🔵 pyenv Python 3.11.8: Missing blake2b/blake2s Hash Support
5468 " 🟣 Three-Tab Scanner Verified Live Against Scan ID 50
5469 " 🟣 New Test: test_scan_has_separate_research_and_methodology_pages
5470 9:34a 🔴 Test Patch Retry: Anchor Mismatch Fixed for test_scan_has_separate_research_and_methodology_pages
5471 " 🟣 Three-Tab Magnetism Scanner: Final Test Suite — 34/34 Passing
5472 " 🟣 Full Magnetism + Research Pipeline Test Suite: 90/90 Passing
5473 " ✅ Dev Server Restarted with New Three-Tab Routes Loaded
5474 9:35a 🟣 Three-Tab Magnetism Scanner: Browser Verification Passed on Scan ID 50
5475 " 🟣 Three-Tab Magnetism Scanner Feature: All Steps Complete
5476 " 🔵 Full Uncommitted Changeset: Three-Tab Scanner Plus Broader Research Pipeline Work

Access 212k tokens of past work via get_observations([IDs]) or mem-search skill.
</claude-mem-context>