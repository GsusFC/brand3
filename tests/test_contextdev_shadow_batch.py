from __future__ import annotations

import json

from scripts.contextdev_attach_candidate_summary_to_run import RAW_INPUT_SOURCE
from scripts.contextdev_shadow_batch import main, render_index_markdown
from src.storage.sqlite_store import SQLiteStore


def test_contextdev_shadow_batch_attaches_summary_and_writes_reports(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "brand3.sqlite3"
    runs_file = tmp_path / "runs.json"
    summary_path = tmp_path / "summary.json"
    output_dir = tmp_path / "batch"

    store = SQLiteStore(str(db_path))
    run_id = _create_run(store, "Example", "https://example.com")
    store.close()

    runs_file.write_text(
        json.dumps([{"run_id": run_id, "brand": "Example", "url": "https://example.com", "label": "run-example"}]),
        encoding="utf-8",
    )
    summary_path.write_text(json.dumps(_summary("https://example.com")), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "contextdev_shadow_batch.py",
            "--runs-file",
            str(runs_file),
            "--summary",
            str(summary_path),
            "--output-dir",
            str(output_dir),
            "--db-path",
            str(db_path),
        ],
    )

    assert main() == 0

    index = json.loads((output_dir / "index.json").read_text(encoding="utf-8"))
    report = json.loads((output_dir / "run-example.json").read_text(encoding="utf-8"))

    assert index["run_count"] == 1
    assert index["evaluated_count"] == 1
    assert index["total_updates"] == 1
    assert report["shadow"]["status"] == "evaluated"
    assert report["shadow"]["field_updates"][0]["candidate_type"] == "visual_fonts"

    store = SQLiteStore(str(db_path))
    try:
        snapshot = store.get_run_snapshot(run_id)
    finally:
        store.close()
    assert snapshot is not None
    assert [item["source"] for item in snapshot["raw_inputs"]].count(RAW_INPUT_SOURCE) == 1


def test_contextdev_shadow_batch_does_not_duplicate_existing_summary(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "brand3.sqlite3"
    runs_file = tmp_path / "runs.json"
    summary_path = tmp_path / "summary.json"
    output_dir = tmp_path / "batch"

    store = SQLiteStore(str(db_path))
    run_id = _create_run(store, "Example", "https://example.com")
    store.save_raw_input(run_id, RAW_INPUT_SOURCE, _summary("https://example.com"))
    store.close()

    runs_file.write_text(json.dumps([{"run_id": run_id, "label": "run-example"}]), encoding="utf-8")
    summary_path.write_text(json.dumps(_summary("https://example.com")), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "contextdev_shadow_batch.py",
            "--runs-file",
            str(runs_file),
            "--summary",
            str(summary_path),
            "--output-dir",
            str(output_dir),
            "--db-path",
            str(db_path),
        ],
    )

    assert main() == 0

    store = SQLiteStore(str(db_path))
    try:
        snapshot = store.get_run_snapshot(run_id)
    finally:
        store.close()
    assert snapshot is not None
    assert [item["source"] for item in snapshot["raw_inputs"]].count(RAW_INPUT_SOURCE) == 1


def test_render_index_markdown_includes_run_counts() -> None:
    markdown = render_index_markdown(
        {
            "run_count": 1,
            "evaluated_count": 1,
            "total_updates": 2,
            "runs": [
                {
                    "run_id": 1,
                    "brand_name": "Example",
                    "shadow_status": "evaluated",
                    "field_update_count": 2,
                    "status_counts": {"promotable": 2, "review_required": 1, "blocked": 0},
                }
            ],
        }
    )

    assert "| 1 | Example | evaluated | 2 | 2 | 1 | 0 |" in markdown


def _create_run(store: SQLiteStore, brand_name: str, url: str) -> int:
    brand_id = store.upsert_brand(brand_name, url)
    run_id = store.create_run(brand_id, brand_name, url, use_llm=False, use_social=False)
    store.save_raw_input(run_id, "web", {"canonical_url": url, "markdown_content": "Example is workflow infrastructure."})
    return run_id


def _summary(source_url: str) -> dict[str, object]:
    return {
        "candidate_count": 1,
        "candidates": [
            {
                "candidate_id": "ctxdev_visual_fonts_1",
                "candidate_type": "visual_fonts",
                "supports_channel": "visual_identity",
                "text": "Aeonik",
                "source_url": source_url,
                "provider": "contextdev",
                "raw_ref": "test",
            }
        ],
    }
