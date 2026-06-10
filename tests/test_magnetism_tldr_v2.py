from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from src.features.magnetism.analyst_tldr import maybe_build_analyst_tldr
from src.features.magnetism.tldr_v2 import build_audit_aware_tldr_v2
from src.models.brand import BrandScore, FeatureValue
from src.scoring.engine import ScoringEngine
from src.scoring.provenance import build_score_provenance_report
from src.scoring.replay import DIMENSIONS_PATH, ENGINE_PATH, _compute_scoring_state_fingerprint
from src.storage.sqlite_store import SQLiteStore


class FakeAnalystLLM:
    def __init__(self, response: dict):
        self.api_key = "valid-key"
        self.response = response

    def _call_json(self, system: str, user: str, max_tokens: int = 8000, **kwargs):
        self.captured_system = system
        self.captured_user = user
        self.captured_kwargs = kwargs
        return self.response


def _research_pack() -> dict:
    return {
        "research_pack": {
            "brand_name": "Example",
            "url": "https://example.com",
        }
    }


def _current_tldr() -> dict:
    llm = FakeAnalystLLM(
        {
            "tldr_brand3": {
                "value_proposition": {
                    "answer": "AI app builder for non-technical founders.",
                    "claim_type": "declared",
                    "mode": "compressed",
                    "confidence": "high",
                    "reasoning": "Literal offer language.",
                    "evidence_used": ["Example is an AI app builder for non-technical founders."],
                    "evidence_sources": [{"source_key": "https://example.com", "source_type": "owned_official"}],
                    "counter_evidence": [],
                    "human_review_recommended": False,
                }
            }
        }
    )
    result = maybe_build_analyst_tldr(
        llm=llm,
        brand_name="Example",
        url="https://example.com",
        research_pack=_research_pack(),
        current_tldr={},
    )
    assert result is not None
    return result


def _feature_fixture(*, presence_low: bool = False) -> dict[str, dict[str, FeatureValue]]:
    presencia_web = 5.0 if presence_low else 90.0
    presencia_social = 5.0 if presence_low else 75.0
    return {
        "coherencia": {
            "visual_consistency": FeatureValue("visual_consistency", 80.0, confidence=0.9, source="web_scrape"),
            "messaging_consistency": FeatureValue("messaging_consistency", 60.0, confidence=0.8, source="llm"),
            "tone_consistency": FeatureValue("tone_consistency", 70.0, confidence=0.8, source="llm"),
            "cross_channel_coherence": FeatureValue("cross_channel_coherence", 50.0, confidence=0.7, source="web_scrape"),
        },
        "presencia": {
            "web_presence": FeatureValue("web_presence", presencia_web, confidence=0.9, source="web_scrape"),
            "social_footprint": FeatureValue("social_footprint", presencia_social, confidence=0.9, source="social_media"),
            "search_visibility": FeatureValue("search_visibility", 80.0, confidence=0.8, source="exa"),
            "directory_presence": FeatureValue("directory_presence", 30.0, confidence=0.8, source="exa"),
        },
        "percepcion": {
            "brand_sentiment": FeatureValue("brand_sentiment", 70.0, confidence=0.8, source="llm"),
            "mention_volume": FeatureValue("mention_volume", 65.0, confidence=0.9, source="exa"),
            "sentiment_trend": FeatureValue("sentiment_trend", 55.0, confidence=0.8, source="llm"),
            "review_quality": FeatureValue("review_quality", 50.0, confidence=0.8, source="exa"),
        },
        "diferenciacion": {
            "positioning_clarity": FeatureValue("positioning_clarity", 75.0, confidence=0.8, source="llm"),
            "uniqueness": FeatureValue("uniqueness", 70.0, confidence=0.8, source="llm"),
            "competitor_distance": FeatureValue("competitor_distance", 70.0, confidence=0.8, source="llm"),
            "content_authenticity": FeatureValue("content_authenticity", 85.0, confidence=0.8, source="content_analysis"),
            "brand_personality": FeatureValue("brand_personality", 80.0, confidence=0.8, source="content_analysis"),
        },
        "vitalidad": {
            "content_recency": FeatureValue("content_recency", 90.0, confidence=0.9, source="exa"),
            "publication_cadence": FeatureValue("publication_cadence", 80.0, confidence=0.9, source="exa"),
            "momentum": FeatureValue("momentum", 60.0, confidence=0.8, source="llm"),
        },
    }


def _seed_run(
    store: SQLiteStore,
    *,
    partial_dimensions: list[str] | None = None,
    unavailable_dimensions: list[str] | None = None,
    artifact_partial_dimensions: list[str] | None = None,
    presence_low: bool = False,
    remove_fingerprint: bool = False,
) -> tuple[int, float]:
    brand_id = store.upsert_brand("Example", "https://example.com")
    run_id = store.create_run(brand_id, "Example", "https://example.com", True, False)
    features_by_dim = _feature_fixture(presence_low=presence_low)
    persisted: dict[str, dict[str, FeatureValue]] = {}
    for dimension_name, features in features_by_dim.items():
        if partial_dimensions and dimension_name in partial_dimensions:
            continue
        persisted[dimension_name] = features

    engine = ScoringEngine()
    brand_score = engine.score_brand(
        "https://example.com",
        "Example",
        persisted,
        unavailable_dimensions=set(unavailable_dimensions if unavailable_dimensions is not None else (partial_dimensions or [])),
    )
    store.save_features(run_id, persisted)
    store.save_scores(
        run_id,
        BrandScore(
            url="https://example.com",
            brand_name="Example",
            dimensions=brand_score.dimensions,
            composite_score=brand_score.composite_score,
        ),
    )

    gate_config = {
        "max_composite_drop": 0.0,
        "max_dimension_drops": {
            "coherencia": 5.0,
            "presencia": 5.0,
            "percepcion": 5.0,
            "diferenciacion": 5.0,
            "vitalidad": 5.0,
        },
    }
    store.upsert_gate_config(gate_config)
    fingerprint = _compute_scoring_state_fingerprint(
        dimensions_content=DIMENSIONS_PATH.read_text(encoding="utf-8"),
        engine_content=ENGINE_PATH.read_text(encoding="utf-8"),
        gate_config=gate_config,
        calibration_profile="base",
        calibration_profile_config=engine.profile_config,
    )
    if not remove_fingerprint:
        store.save_run_audit(
            run_id,
            {
                "gate_config": gate_config,
                "active_baseline": None,
                "scoring_state_fingerprint": fingerprint,
            },
        )

    artifact = {
        "run_id": run_id,
        "brand_name": "Example",
        "url": "https://example.com",
        "composite_score": brand_score.composite_score,
        "dimensions": brand_score.breakdown,
        "partial_dimensions": list(artifact_partial_dimensions if artifact_partial_dimensions is not None else (partial_dimensions or [])),
        "partial_score": False,
    }
    artifact_path = Path(store.db_path).with_name(f"tldr-v2-{run_id}.json")
    artifact_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    store.finalize_run(run_id, brand_score.composite_score, True, False, str(artifact_path), "summary")
    return run_id, float(brand_score.composite_score or 0.0)


class AuditAwareTLDRV2Tests(unittest.TestCase):
    def test_current_tldr_remains_unchanged(self):
        current = _current_tldr()
        baseline = deepcopy(current)

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _ = _seed_run(store)
            provenance = build_score_provenance_report(store, run_id)

            v2 = build_audit_aware_tldr_v2(score_provenance=provenance, current_tldr=current["tldr_brand3"])
            store.close()

        self.assertEqual(current, baseline)
        self.assertIn("tldr_brand3_v2", v2)

    def test_v2_uses_computed_score_when_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, computed = _seed_run(store)
            provenance = build_score_provenance_report(store, run_id)

            v2 = build_audit_aware_tldr_v2(score_provenance=provenance, current_tldr={})
            store.close()

        self.assertEqual(v2["score_state"]["display_score_source"], "computed")
        self.assertEqual(v2["score_state"]["recommended_display_score"], computed)

    def test_v2_uses_reviewed_score_when_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _ = _seed_run(store)
            store.save_reviewed_score(
                run_id,
                reviewed_composite_score=78.0,
                reason="Human reviewer adjusted the score after checking the evidence trail.",
                evidence_refs=["https://example.com"],
                reviewer="reviewer-a",
                affected_dimensions=["presencia", "diferenciacion"],
                review_status="adjusted",
            )
            provenance = build_score_provenance_report(store, run_id)

            v2 = build_audit_aware_tldr_v2(score_provenance=provenance, current_tldr={})
            store.close()

        self.assertEqual(v2["score_state"]["display_score_source"], "reviewed")
        self.assertEqual(v2["score_state"]["recommended_display_score"], 78.0)
        self.assertEqual(v2["score_state"]["reviewed_composite_score"], 78.0)

    def test_v2_blocks_score_when_drift_detected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _ = _seed_run(store)
            store.conn.execute(
                """
                UPDATE features
                SET value = ?
                WHERE run_id = ? AND dimension_name = ? AND feature_name = ?
                """,
                (5.0, run_id, "presencia", "web_presence"),
            )
            store.conn.commit()
            provenance = build_score_provenance_report(store, run_id)

            v2 = build_audit_aware_tldr_v2(score_provenance=provenance, current_tldr={})
            store.close()

        self.assertEqual(v2["score_state"]["display_score_source"], "blocked")
        self.assertEqual(v2["score_state"]["display_score_status"], "blocked")
        self.assertIsNone(v2["score_state"]["recommended_display_score"])
        self.assertTrue(v2["score_state"]["display_score_blocked"])

    def test_v2_warns_on_fallback_50(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _ = _seed_run(
                store,
                partial_dimensions=["presencia"],
                unavailable_dimensions=[],
                artifact_partial_dimensions=[],
            )
            provenance = build_score_provenance_report(store, run_id)

            v2 = build_audit_aware_tldr_v2(score_provenance=provenance, current_tldr={})
            store.close()

        self.assertIn("presencia", v2["score_state"]["fallback_flags"]["replay_neutral_fallback_dimensions"])
        self.assertTrue(
            any(issue.get("code") == "neutral_fallback_dimension" for issue in v2["score_state"]["warnings"])
        )

    def test_v2_exposes_low_confidence_scoring(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "brand3.sqlite3"))
            run_id, _ = _seed_run(store, remove_fingerprint=True)
            provenance = build_score_provenance_report(store, run_id)

            v2 = build_audit_aware_tldr_v2(score_provenance=provenance, current_tldr={})
            store.close()

        self.assertEqual(v2["score_state"]["display_score_status"], "limited_confidence")
        self.assertTrue(v2["score_state"]["limited_confidence"])
        self.assertEqual(v2["score_state"]["display_score_source"], "computed")


if __name__ == "__main__":
    unittest.main()
