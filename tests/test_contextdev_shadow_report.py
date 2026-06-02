from __future__ import annotations

import json

from scripts.contextdev_attach_candidate_summary_to_run import RAW_INPUT_SOURCE
from scripts.contextdev_shadow_report import main, render_markdown
from src.storage.sqlite_store import SQLiteStore


def test_contextdev_shadow_report_writes_json_and_markdown(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "brand3.sqlite3"
    output_json = tmp_path / "report.json"
    output_md = tmp_path / "report.md"
    store = SQLiteStore(str(db_path))
    brand_id = store.upsert_brand("Example", "https://example.com")
    run_id = store.create_run(brand_id, "Example", "https://example.com", use_llm=False, use_social=False)
    store.save_raw_input(
        run_id,
        "web",
        {
            "canonical_url": "https://example.com",
            "markdown_content": "Example is workflow infrastructure for finance operators.",
        },
    )
    store.save_raw_input(
        run_id,
        RAW_INPUT_SOURCE,
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
                    "raw_ref": "test",
                }
            ],
        },
    )
    store.close()

    monkeypatch.setattr(
        "sys.argv",
        [
            "contextdev_shadow_report.py",
            "--run-id",
            str(run_id),
            "--db-path",
            str(db_path),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
    )

    assert main() == 0

    report = json.loads(output_json.read_text(encoding="utf-8"))
    markdown = output_md.read_text(encoding="utf-8")

    assert report["version"] == "contextdev_shadow_report_v0_1"
    assert report["shadow"]["status"] == "evaluated"
    assert report["shadow"]["field_update_count"] == 1
    assert report["shadow"]["field_updates"][0]["candidate_type"] == "visual_fonts"
    assert "# Context.dev Shadow Report" in markdown
    assert "`visual_or_conceptual_signals` append from `visual_fonts`" in markdown


def test_render_markdown_handles_missing_updates() -> None:
    markdown = render_markdown(
        {
            "run_id": 1,
            "brand_name": "Example",
            "url": "https://example.com",
            "tldr_generation_mode": "legacy_fallback_no_llm",
            "research_pack": {
                "source": "snapshot_builder",
                "visual_signal_count": 0,
                "confidence_note_count": 0,
                "product_summary": "",
            },
            "shadow": {
                "status": "skipped",
                "field_update_count": 0,
                "status_counts": {},
                "field_updates": [
                    {
                        "field": "confidence_notes",
                        "action": "append",
                        "candidate_type": "product_profile",
                        "value": "x" * 400,
                    }
                ],
            },
        }
    )

    assert "xxx..." in markdown
    assert "No promotion counts available." in markdown
