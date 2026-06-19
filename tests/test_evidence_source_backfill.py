from types import SimpleNamespace

from scripts.evidence_source_backfill import build_source_backfill, render_source_backfill_markdown


def _repair_board() -> dict:
    return {
        "cards": [
            {
                "record_id": "decision_273_backfill_source_url_or_remove_material",
                "run_id": 273,
                "brand_name": "causaprima.ai",
                "recommended_decision": "source_url_attached_or_exclude_unsourced_quote",
                "source_backfill_queries": [
                    '"Unlike existing finance tools built to serve one side of a transaction, Causa Prima puts buyers and suppliers on the same network." causaprima.ai'
                ],
                "record": {
                    "quote_text": '"Unlike existing finance tools built to serve one side of a transaction, Causa Prima puts buyers and suppliers on the same network." causaprima.ai'
                },
            }
        ]
    }


def test_source_backfill_dry_run_inventories_queries_without_candidates() -> None:
    payload = build_source_backfill(_repair_board(), execute=False)
    markdown = render_source_backfill_markdown(payload)

    assert payload["runtime_effect"] is False
    assert payload["persistence_effect"] is False
    assert payload["summary"]["record_count"] == 1
    assert payload["summary"]["query_count"] == 1
    assert payload["summary"]["candidate_count"] == 0
    assert payload["summary"]["suggested_patch_count"] == 0
    assert "Evidence Source Backfill" in markdown


def test_source_backfill_suggests_sourced_equivalent_for_high_overlap() -> None:
    def searcher(query, context):
        return [
            SimpleNamespace(
                url="https://pathfounders.com/p/causa-prima",
                title="Causa Prima raises $10M",
                text=(
                    "While existing finance software generally serves either the buyer or supplier, "
                    "Causa Prima connects both parties on the same network."
                ),
                summary="",
                highlights=[],
                published_date="2026-06-16",
                source_class="external",
                requires_human_review=False,
            )
        ]

    payload = build_source_backfill(_repair_board(), execute=True, searcher=searcher)
    best = payload["rows"][0]["best_candidate"]

    assert payload["summary"]["candidate_count"] == 1
    assert payload["summary"]["suggested_patch_count"] == 1
    assert best["suggested_decision"] == "replace_with_sourced_equivalent"
    assert best["claim_overlap_score"] >= 0.28
    assert best["url"] == "https://pathfounders.com/p/causa-prima"
    patch = payload["rows"][0]["suggested_record_patch"]
    assert patch["decision"] == "replace_with_sourced_equivalent"
    assert patch["source_url"] == "https://pathfounders.com/p/causa-prima"
    assert "Causa Prima connects both parties on the same network" in patch["replacement_quote"]


def test_source_backfill_suggests_source_url_attached_for_exact_match() -> None:
    exact = (
        "Unlike existing finance tools built to serve one side of a transaction, "
        "Causa Prima puts buyers and suppliers on the same network."
    )

    def searcher(query, context):
        return [
            {
                "url": "https://example.com/source",
                "title": "Exact source",
                "text": exact,
                "source_class": "external",
                "requires_human_review": False,
            }
        ]

    payload = build_source_backfill(_repair_board(), execute=True, searcher=searcher)
    best = payload["rows"][0]["best_candidate"]

    assert best["exact_quote_match"] is True
    assert best["suggested_decision"] == "source_url_attached"
    assert payload["rows"][0]["suggested_record_patch"]["decision"] == "source_url_attached"
