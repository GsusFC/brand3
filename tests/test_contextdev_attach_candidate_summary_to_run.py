from __future__ import annotations

import json

from scripts.contextdev_attach_candidate_summary_to_run import main
from src.storage.sqlite_store import SQLiteStore


def test_contextdev_attach_candidate_summary_to_run_persists_raw_input(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "brand3.sqlite3"
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "candidate_count": 1,
                "candidates": [
                    {
                        "candidate_id": "ctxdev_visual_fonts_1",
                        "candidate_type": "visual_fonts",
                        "supports_channel": "visual_identity",
                        "text": "Aeonik",
                        "source_url": "https://example.com",
                        "provider": "contextdev",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    store = SQLiteStore(str(db_path))
    brand_id = store.upsert_brand("Example", "https://example.com")
    run_id = store.create_run(brand_id, "Example", "https://example.com", use_llm=False, use_social=False)
    store.close()

    monkeypatch.setattr(
        "sys.argv",
        [
            "contextdev_attach_candidate_summary_to_run.py",
            "--run-id",
            str(run_id),
            "--summary",
            str(summary_path),
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
    raw_inputs = snapshot["raw_inputs"]
    assert raw_inputs[-1]["source"] == "contextdev_candidate_summary"
    assert raw_inputs[-1]["payload"]["candidate_count"] == 1
