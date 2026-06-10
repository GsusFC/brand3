from __future__ import annotations

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from src.reports.experimental_perceptual_narrative import (
    build_perceptual_narrative_hints,
    _stable_case_records,
    format_perceptual_hints_for_prompt,
)
from src.reports.perceptual_corpus import (
    PERCEPTUAL_ROOT,
    PerceptualCorpusError,
    load_perceptual_artifacts,
    load_perceptual_case_record,
    validate_perceptual_case_record,
)


class PerceptualCorpusTests(unittest.TestCase):
    def test_loads_twelve_case_records_after_non_web3_batch(self):
        artifacts = load_perceptual_artifacts()

        self.assertIn("registry", artifacts)
        self.assertIn("semantics", artifacts)
        self.assertEqual(len(artifacts["case_records"]), 12)
        self.assertEqual(
            [record["case_id"] for record in artifacts["case_records"]],
            [
                "blockdyne_master_brand3",
                "clcripto_tldr",
                "eaship_brand3_magnetism_scan",
                "esco_token_brand_platform_v3",
                "irisdesign_dev",
                "launchdarkly",
                "meta4_english",
                "nektar_summary_brand_platform",
                "rosalind_brand3_landing",
                "sova_analysis",
                "sova_prueba_llm_estrategia",
                "watermelon_sh",
            ],
        )
        self.assertTrue(all("domain_context" in record for record in artifacts["case_records"]))

    def test_stable_case_records_excludes_review_only_records(self):
        artifacts = load_perceptual_artifacts()
        stable = _stable_case_records(artifacts["case_records"])

        self.assertTrue(all(isinstance(record.get("domain_context"), dict) for record in stable))
        self.assertTrue(all(record.get("domain_context", {}).get("normalization_status") == "normalized" for record in stable))
        stable_case_ids = {record.get("case_id") for record in stable}
        self.assertNotIn("meta4_english", stable_case_ids)
        self.assertNotIn("sova_prueba_llm_estrategia", stable_case_ids)

    def test_valid_case_record_has_separated_sections(self):
        record = load_perceptual_case_record(
            PERCEPTUAL_ROOT / "cases" / "rosalind_brand3_landing" / "perceptual_case_record.json"
        )

        self.assertIn("domain_context", record)
        self.assertIn("extracted_facts", record)
        self.assertIn("visual_observations", record)
        self.assertIn("strategic_interpretation", record)
        self.assertIn("pattern_refs", record)
        self.assertIn("weak_inferences", record)
        self.assertIn("human_review_requirements", record)
        self.assertEqual(record["domain_context"]["normalization_status"], "normalized")
        self.assertTrue(all("fact" in item for item in record["extracted_facts"]))
        self.assertTrue(all("observation" in item for item in record["visual_observations"]))
        self.assertTrue(all("interpretation" in item for item in record["strategic_interpretation"]))
        self.assertTrue(all("pattern_id" in item for item in record["pattern_refs"]))
        self.assertTrue(all("pattern_name" in item for item in record["pattern_refs"]))
        self.assertTrue(all("reason" in item for item in record["pattern_refs"]))
        self.assertTrue(all("confidence" in item for item in record["pattern_refs"]))
        self.assertTrue(all("evidence_refs" in item for item in record["pattern_refs"]))
        self.assertTrue(all("inference" in item for item in record["weak_inferences"]))
        self.assertTrue(all("requirement" in item for item in record["human_review_requirements"]))

    def test_validate_rejects_missing_section(self):
        invalid = {
            "schema_version": "perceptual_case_record_v1",
            "record_type": "perceptual_case_record",
            "case_id": "broken",
            "brand_name": "Broken",
            "document_title": "Broken",
            "source_ref": "docs/example.md",
            "workspace_location": "FLOC*Ops / Projects Database / Broken",
            "source_family": "client_brand3_tldr",
            "status": "client_deliverable",
            "language": "en",
            "company_context": {
                "company_name": "Broken",
                "category": "example",
                "business_model": "service",
                "offer_summary": "broken",
                "target_audience_summary": "broken",
                "stage_or_context": "unknown",
                "project_scope": "Brand3",
                "source_confidence": "low",
                "sensitive_notes": "",
            },
            "domain_context": {
                "original_domain": "culture",
                "technology_context": [],
                "traditional_equivalent_category": "brand strategy",
                "business_model_analogy": "creative services engagement",
                "transferable_brand_patterns": ["Evidence-Bound Behavior"],
                "domain_specific_noise": [],
                "normalization_status": "normalized",
            },
            "extracted_facts": [],
            "visual_observations": [],
            "strategic_interpretation": [],
            "pattern_refs": [],
            "weak_inferences": [],
            # human_review_requirements is intentionally omitted
        }

        with self.assertRaises(PerceptualCorpusError):
            validate_perceptual_case_record(invalid)

    def test_validate_rejects_missing_pattern_refs(self):
        invalid = {
            "schema_version": "perceptual_case_record_v1",
            "record_type": "perceptual_case_record",
            "case_id": "broken-pattern-refs",
            "brand_name": "Broken Pattern Refs",
            "document_title": "Broken Pattern Refs",
            "source_ref": "docs/example.md",
            "workspace_location": "FLOC*Ops / Projects Database / Broken Pattern Refs",
            "source_family": "client_brand3_tldr",
            "status": "client_deliverable",
            "language": "en",
            "company_context": {
                "company_name": "Broken Pattern Refs",
                "category": "example",
                "business_model": "service",
                "offer_summary": "broken",
                "target_audience_summary": "broken",
                "stage_or_context": "unknown",
                "project_scope": "Brand3",
                "source_confidence": "low",
                "sensitive_notes": "",
            },
            "domain_context": {
                "original_domain": "culture",
                "technology_context": [],
                "traditional_equivalent_category": "brand strategy",
                "business_model_analogy": "creative services engagement",
                "transferable_brand_patterns": ["Evidence-Bound Behavior"],
                "domain_specific_noise": [],
                "normalization_status": "normalized",
            },
            "extracted_facts": [],
            "visual_observations": [],
            "strategic_interpretation": [],
            "weak_inferences": [],
            "human_review_requirements": [],
        }

        with self.assertRaises(PerceptualCorpusError):
            validate_perceptual_case_record(invalid)

    def test_validate_rejects_invalid_pattern_ref_shape(self):
        invalid = {
            "schema_version": "perceptual_case_record_v1",
            "record_type": "perceptual_case_record",
            "case_id": "broken-pattern-ref",
            "brand_name": "Broken Pattern",
            "document_title": "Broken Pattern",
            "source_ref": "docs/example.md",
            "workspace_location": "FLOC*Ops / Projects Database / Broken Pattern",
            "source_family": "client_brand3_tldr",
            "status": "client_deliverable",
            "language": "en",
            "company_context": {
                "company_name": "Broken Pattern",
                "category": "example",
                "business_model": "service",
                "offer_summary": "broken",
                "target_audience_summary": "broken",
                "stage_or_context": "unknown",
                "project_scope": "Brand3",
                "source_confidence": "low",
                "sensitive_notes": "",
            },
            "domain_context": {
                "original_domain": "culture",
                "technology_context": [],
                "traditional_equivalent_category": "brand strategy",
                "business_model_analogy": "creative services engagement",
                "transferable_brand_patterns": ["Evidence-Bound Behavior"],
                "domain_specific_noise": [],
                "normalization_status": "normalized",
            },
            "extracted_facts": [],
            "visual_observations": [],
            "strategic_interpretation": [],
            "pattern_refs": [
                {
                    "pattern_id": "pattern_claim_signal_gap",
                    "pattern_name": "Claim / Signal Gap",
                    "reason": "Valid pattern reference needs evidence refs",
                    "confidence": "medium",
                }
            ],
            "weak_inferences": [],
            "human_review_requirements": [],
        }

        with self.assertRaises(PerceptualCorpusError):
            validate_perceptual_case_record(invalid)

    def test_validate_rejects_web3_record_without_traditional_equivalent(self):
        invalid = {
            "schema_version": "perceptual_case_record_v1",
            "record_type": "perceptual_case_record",
            "case_id": "broken-web3-normalization",
            "brand_name": "Broken Web3",
            "document_title": "Broken Web3",
            "source_ref": "https://app.notion.com/p/example",
            "workspace_location": "FLOC*Ops / Projects Database / Broken Web3",
            "source_family": "client_brand_platform",
            "status": "active_source_of_truth",
            "language": "en",
            "company_context": {
                "company_name": "Broken Web3",
                "category": "example",
                "business_model": "service",
                "offer_summary": "broken",
                "target_audience_summary": "broken",
                "stage_or_context": "unknown",
                "project_scope": "Brand3",
                "source_confidence": "low",
                "sensitive_notes": "",
            },
            "domain_context": {
                "original_domain": "web3",
                "technology_context": ["token"],
                "business_model_analogy": "service",
                "transferable_brand_patterns": ["Evidence-Bound Behavior"],
                "domain_specific_noise": ["token"],
                "normalization_status": "normalized",
            },
            "extracted_facts": [],
            "visual_observations": [],
            "strategic_interpretation": [],
            "pattern_refs": [
                {
                    "pattern_id": "pattern_evidence_bound_behavior",
                    "pattern_name": "Evidence-Bound Behavior",
                    "reason": "bounded reading",
                    "confidence": "high",
                    "evidence_refs": ["https://app.notion.com/p/example"],
                }
            ],
            "weak_inferences": [],
            "human_review_requirements": [],
        }

        with self.assertRaises(PerceptualCorpusError):
            validate_perceptual_case_record(invalid)

    def test_validate_allows_non_web3_record_without_traditional_equivalent(self):
        valid = {
            "schema_version": "perceptual_case_record_v1",
            "record_type": "perceptual_case_record",
            "case_id": "culture-normalization",
            "brand_name": "Culture Example",
            "document_title": "Culture Example",
            "source_ref": "https://app.notion.com/p/example",
            "workspace_location": "FLOC*Ops / Projects Database / Culture Example",
            "source_family": "client_brand3_tldr",
            "status": "client_deliverable",
            "language": "en",
            "company_context": {
                "company_name": "Culture Example",
                "category": "example",
                "business_model": "service",
                "offer_summary": "example",
                "target_audience_summary": "example",
                "stage_or_context": "unknown",
                "project_scope": "Brand3",
                "source_confidence": "low",
                "sensitive_notes": "",
            },
            "domain_context": {
                "original_domain": "culture",
                "technology_context": [],
                "business_model_analogy": "creative services engagement",
                "transferable_brand_patterns": ["Evidence-Bound Behavior"],
                "domain_specific_noise": [],
                "normalization_status": "normalized",
            },
            "extracted_facts": [],
            "visual_observations": [],
            "strategic_interpretation": [],
            "pattern_refs": [
                {
                    "pattern_id": "pattern_evidence_bound_behavior",
                    "pattern_name": "Evidence-Bound Behavior",
                    "reason": "bounded reading",
                    "confidence": "high",
                    "evidence_refs": ["https://app.notion.com/p/example"],
                }
            ],
            "weak_inferences": [],
            "human_review_requirements": [],
        }

        validate_perceptual_case_record(valid)

    def test_build_perceptual_narrative_hints_uses_pilot_records(self):
        hints = build_perceptual_narrative_hints("percepcion")

        self.assertGreaterEqual(len(hints.surface_signals), 3)
        self.assertIn("Category-To-Surface Translation", {pattern["pattern_name"] for pattern in hints.matched_patterns})
        self.assertTrue(any(note.startswith("medium:") for note in hints.confidence_notes))
        self.assertTrue(any("partially corroborated" in note for note in hints.confidence_notes))
        self.assertTrue(any("Do not treat category ambition as proven market position." in boundary for boundary in hints.overreach_boundaries))
        self.assertTrue(
            any(
                "infrastructure" in signal.lower()
                or "compact block" in signal.lower()
                or "crypto" in signal.lower()
                for signal in hints.surface_signals
            )
        )

    def test_build_perceptual_narrative_hints_is_deterministic_and_domain_bounded(self):
        hints_a = build_perceptual_narrative_hints("percepcion")
        hints_b = build_perceptual_narrative_hints("percepcion")

        self.assertEqual(hints_a.surface_signals, hints_b.surface_signals)
        self.assertEqual(hints_a.surface_signal_details, hints_b.surface_signal_details)

        domains = Counter(detail["original_domain"] for detail in hints_a.surface_signal_details)
        patterns = Counter(detail["selected_pattern_id"] for detail in hints_a.surface_signal_details)
        self.assertLessEqual(max(domains.values()), 2)
        self.assertLessEqual(max(patterns.values()), 2)
        self.assertTrue(any(domain != "web3" and domain != "crypto" for domain in domains))
        self.assertTrue(
            any(
                case_id in {"irisdesign_dev", "launchdarkly", "watermelon_sh"}
                for case_id in {detail["case_id"] for detail in hints_a.surface_signal_details}
            )
        )
        self.assertTrue(all(detail["evidence_refs"] for detail in hints_a.surface_signal_details))
        prompt = format_perceptual_hints_for_prompt(hints_a)
        self.assertIn("Surface signal evidence:", prompt)
        self.assertTrue(any(ref in prompt for detail in hints_a.surface_signal_details for ref in detail["evidence_refs"]))

    def test_unnormalized_and_review_only_records_are_filtered_from_stable_narrative_hints(self):
        from src.reports import experimental_perceptual_narrative as experimental

        experimental._load_artifacts.cache_clear()
        original_loader = experimental.load_perceptual_artifacts
        try:
            experimental.load_perceptual_artifacts = lambda: {
                "registry": {
                    "patterns": [
                        {
                            "pattern_id": "pattern_evidence_bound_behavior",
                            "pattern_name": "Evidence-Bound Behavior",
                            "perceptual_meaning": "The reading stays useful by naming what the evidence can and cannot support.",
                            "confidence_level": "medium",
                            "typical_tensions": ["available owned evidence vs missing external corroboration"],
                        }
                    ]
                },
                "semantics": {
                    "definitions": {
                        "signal_clusters": {"examples": []},
                        "perceptual_confidence": {
                            "levels": {
                                "high": "high confidence",
                                "medium": "medium confidence",
                                "low": "low confidence",
                            }
                        },
                    },
                    "overreach_examples": [],
                    "generic_llm_interpretation_to_avoid": [],
                },
                "case_records": [
                    {
                        "case_id": "normalized",
                        "domain_context": {"normalization_status": "normalized"},
                        "pattern_refs": [
                            {
                                "pattern_id": "pattern_evidence_bound_behavior",
                                "pattern_name": "Evidence-Bound Behavior",
                                "reason": "bounded reading",
                                "confidence": "medium",
                                "evidence_refs": ["https://example.com/normalized"],
                            }
                        ],
                        "visual_observations": [
                            {
                                "observation": "Normalized surface signal",
                                "evidence_refs": ["https://example.com/normalized"],
                            }
                        ],
                    },
                    {
                        "case_id": "review-only",
                        "domain_context": {"normalization_status": "needs_human_review"},
                        "pattern_refs": [
                            {
                                "pattern_id": "pattern_claim_signal_gap",
                                "pattern_name": "Claim / Signal Gap",
                                "reason": "review only",
                                "confidence": "low",
                                "evidence_refs": ["https://example.com/review-only"],
                            }
                        ],
                        "visual_observations": [
                            {
                                "observation": "Review-only surface signal",
                                "evidence_refs": ["https://example.com/review-only"],
                            }
                        ],
                    },
                    {
                        "domain_context": {"normalization_status": "needs_human_review"},
                        "pattern_refs": [
                            {
                                "pattern_id": "pattern_claim_signal_gap",
                                "pattern_name": "Claim / Signal Gap",
                                "reason": "unnormalized",
                                "confidence": "low",
                                "evidence_refs": ["https://example.com/unnormalized"],
                            }
                        ],
                        "visual_observations": [
                            {
                                "observation": "Unnormalized surface signal",
                                "evidence_refs": ["https://example.com/unnormalized"],
                            }
                        ],
                    },
                ],
            }
            hints = experimental.build_perceptual_narrative_hints("percepcion")
            self.assertEqual(hints.surface_signals, ["Normalized surface signal"])
            self.assertEqual(len(hints.surface_signal_details), 1)
            self.assertEqual(hints.surface_signal_details[0]["case_id"], "normalized")
            self.assertEqual(hints.surface_signal_details[0]["evidence_refs"], ["https://example.com/normalized"])
        finally:
            experimental.load_perceptual_artifacts = original_loader
            experimental._load_artifacts.cache_clear()

    def test_corpus_files_are_valid_json(self):
        for path in sorted((PERCEPTUAL_ROOT / "cases").glob("*/perceptual_case_record.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["record_type"], "perceptual_case_record")
            validate_perceptual_case_record(payload)

    def test_expansion_batch_one_cases_use_canonical_urls_and_pattern_refs(self):
        case_paths = [
            PERCEPTUAL_ROOT / "cases" / "blockdyne_master_brand3" / "perceptual_case_record.json",
            PERCEPTUAL_ROOT / "cases" / "clcripto_tldr" / "perceptual_case_record.json",
            PERCEPTUAL_ROOT / "cases" / "meta4_english" / "perceptual_case_record.json",
        ]

        for path in case_paths:
            payload = load_perceptual_case_record(path)
            self.assertTrue(payload["source_ref"].startswith("https://app.notion.com/p/"))
            self.assertTrue(payload["pattern_refs"])
            self.assertTrue(all(item["evidence_refs"] for item in payload["pattern_refs"]))
            self.assertIn(payload["domain_context"]["normalization_status"], {"normalized", "needs_human_review"})
            if payload["domain_context"]["original_domain"] in {"web3", "crypto"}:
                self.assertTrue(payload["domain_context"]["domain_specific_noise"])
                self.assertTrue(payload["domain_context"]["traditional_equivalent_category"])

    def test_expansion_batch_two_cases_use_canonical_urls_and_pattern_refs(self):
        case_paths = [
            PERCEPTUAL_ROOT / "cases" / "sova_analysis" / "perceptual_case_record.json",
            PERCEPTUAL_ROOT / "cases" / "sova_prueba_llm_estrategia" / "perceptual_case_record.json",
            PERCEPTUAL_ROOT / "cases" / "eaship_brand3_magnetism_scan" / "perceptual_case_record.json",
        ]

        for path in case_paths:
            payload = load_perceptual_case_record(path)
            self.assertTrue(payload["source_ref"].startswith("https://app.notion.com/p/"))
            self.assertTrue(payload["pattern_refs"])
            self.assertTrue(all(item["evidence_refs"] for item in payload["pattern_refs"]))
            self.assertIn(payload["domain_context"]["normalization_status"], {"normalized", "needs_human_review"})
            if payload["domain_context"]["original_domain"] in {"web3", "crypto"}:
                self.assertTrue(payload["domain_context"]["domain_specific_noise"])
                self.assertTrue(payload["domain_context"]["traditional_equivalent_category"])
            else:
                self.assertEqual(payload["domain_context"]["original_domain"], "SaaS")

    def test_expansion_batch_three_non_web3_cases_use_canonical_urls_and_pattern_refs(self):
        case_paths = [
            PERCEPTUAL_ROOT / "cases" / "irisdesign_dev" / "perceptual_case_record.json",
            PERCEPTUAL_ROOT / "cases" / "launchdarkly" / "perceptual_case_record.json",
            PERCEPTUAL_ROOT / "cases" / "watermelon_sh" / "perceptual_case_record.json",
        ]

        for path in case_paths:
            payload = load_perceptual_case_record(path)
            self.assertTrue(payload["source_ref"].startswith("https://"))
            self.assertTrue(payload["pattern_refs"])
            self.assertTrue(all(item["evidence_refs"] for item in payload["pattern_refs"]))
            self.assertNotIn(payload["domain_context"]["original_domain"], {"web3", "crypto"})
            self.assertEqual(payload["domain_context"]["normalization_status"], "normalized")
            self.assertTrue(payload["domain_context"]["transferable_brand_patterns"])

    def test_review_only_batch_two_record_is_not_used_for_stable_hints(self):
        hints = build_perceptual_narrative_hints("percepcion")

        self.assertNotIn(
            "The language remains intentionally experimental and explicitly provisional.",
            hints.surface_signals,
        )
