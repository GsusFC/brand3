from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from src.visual_signature.corpus_expansion import (
    build_reviewer_packets,
    validate_reviewer_packets,
    write_reviewer_packets,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_reviewer_packets_cover_selected_pilot_items(tmp_path: Path) -> None:
    outputs = write_reviewer_packets(output_root=tmp_path)
    assert Path(outputs["reviewer_packet_index_md"]).exists()
    assert Path(outputs["reviewer_packet_allbirds"]).exists()
    assert Path(outputs["reviewer_packet_headspace"]).exists()
    assert validate_reviewer_packets(packets_root=tmp_path) == []


def test_reviewer_packet_index_mentions_selected_items(tmp_path: Path) -> None:
    outputs = write_reviewer_packets(output_root=tmp_path)
    index_text = Path(outputs["reviewer_packet_index_md"]).read_text(encoding="utf-8")
    assert "queue_allbirds" in index_text
    assert "queue_headspace" in index_text
    assert "Do not invent evidence." in index_text


def test_packets_do_not_contain_completed_review_records(tmp_path: Path) -> None:
    write_reviewer_packets(output_root=tmp_path)
    allbirds_text = (tmp_path / "allbirds.md").read_text(encoding="utf-8")
    headspace_text = (tmp_path / "headspace.md").read_text(encoding="utf-8")
    assert "This packet does not contain a completed review decision." in allbirds_text
    assert "This packet does not contain a completed review decision." in headspace_text
    assert "review_outcome" in allbirds_text
    assert "review_outcome" in headspace_text


def test_missing_packet_fails_validation(tmp_path: Path) -> None:
    write_reviewer_packets(output_root=tmp_path)
    (tmp_path / "headspace.md").unlink()
    errors = validate_reviewer_packets(packets_root=tmp_path)
    assert any("missing reviewer packet" in error.lower() for error in errors)


def test_packet_generation_is_deterministic_for_selected_items() -> None:
    payload = build_reviewer_packets()
    assert payload["selected_review_queue_item_ids"] == ["queue_allbirds", "queue_headspace"]
    assert payload["readiness_scope"] == "human_review_scaling"
    assert len(payload["packets"]) == 2
    assert payload["packets"][0]["queue_id"] == "queue_allbirds"
    assert payload["packets"][1]["queue_id"] == "queue_headspace"
