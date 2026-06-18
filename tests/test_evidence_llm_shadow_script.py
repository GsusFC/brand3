from __future__ import annotations

from argparse import Namespace

from scripts.evidence_llm_shadow import _brand_key, _llm_for_args, _markdown, _summary


def test_evidence_llm_shadow_summary_counts_status_and_deltas() -> None:
    rows = [
        {
            "llm_status": "ok",
            "llm_transport": "gemini_native",
            "semantic_class_disagreement_count": 2,
            "materiality_disagreement_count": 1,
            "llm_attempt_count": 2,
            "llm_batch_count": 1,
            "llm_retry_count": 1,
            "elapsed_seconds": 1.25,
        },
        {
            "llm_status": "unavailable",
            "llm_transport": "",
            "semantic_class_disagreement_count": 0,
            "materiality_disagreement_count": 0,
            "llm_attempt_count": 0,
            "llm_batch_count": 0,
            "llm_retry_count": 0,
            "elapsed_seconds": 0.75,
        },
    ]

    summary = _summary(rows)

    assert summary["run_count"] == 2
    assert summary["status_counts"] == {"ok": 1, "unavailable": 1}
    assert summary["transport_counts"] == {"gemini_native": 1}
    assert summary["semantic_class_disagreement_count"] == 2
    assert summary["materiality_disagreement_count"] == 1
    assert summary["total_batches"] == 1
    assert summary["total_attempts"] == 2
    assert summary["total_retries"] == 1
    assert summary["total_elapsed_seconds"] == 2.0


def test_evidence_llm_shadow_markdown_renders_rows() -> None:
    markdown = _markdown(
        {
            "runtime_effect": False,
            "prompt_effect": False,
            "persistence_effect": False,
            "summary": {"run_count": 1, "status_counts": {"ok": 1}},
            "rows": [
                {
                    "run_id": 123,
                    "brand_name": "Canva",
                    "llm_status": "ok",
                    "llm_model": "gemini-3.5-flash",
                    "llm_transport": "gemini_native",
                    "accepted_count": 2,
                    "heuristic_accepted_material": 1,
                    "llm_accepted_material": 2,
                    "semantic_class_disagreement_count": 1,
                    "materiality_disagreement_count": 1,
                    "llm_attempt_count": 1,
                    "llm_batch_count": 1,
                    "llm_retry_count": 0,
                    "elapsed_seconds": 0.42,
                }
            ],
        }
    )

    assert "# Evidence LLM Shadow" in markdown
    assert "| 123 | Canva | ok | gemini-3.5-flash | gemini_native | 2 | 1 | 2 | 1 | 1 | 1 | 1 | 0 | 0.42 |" in markdown


def test_evidence_llm_shadow_brand_key_normalizes_url() -> None:
    assert _brand_key({"run": {"brand_name": "Foo", "url": "https://www.foo.com/"}}) == "foo.com"
    assert _brand_key({"run": {"brand_name": "Foo", "url": ""}}) == "foo"


def test_evidence_llm_shadow_no_cache_builds_uncached_llm() -> None:
    assert _llm_for_args(Namespace(no_cache=False)) is None
    llm = _llm_for_args(Namespace(no_cache=True))
    assert llm is not None
    assert llm.use_cache is False
