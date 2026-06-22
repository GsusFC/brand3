from src.visual_signature._internal.utils import (
    dict_or_empty,
    first_dict,
    normalize_capture_type,
    unique_by_key,
    unique_text,
)


def test_unique_text_normalizes_and_deduplicates_values():
    assert unique_text(["  alpha ", "beta", "alpha", "", None, "beta ", 3]) == ["alpha", "beta", "None", "3"]


def test_unique_text_preserves_first_seen_order():
    assert unique_text(["zeta", "alpha", "zeta", "beta", "alpha"]) == ["zeta", "alpha", "beta"]


def test_normalize_capture_type_accepts_expected_values():
    assert normalize_capture_type(" viewport ") == "viewport"
    assert normalize_capture_type("FULL_PAGE") == "full_page"
    assert normalize_capture_type("other") == "unknown"


def test_dict_or_empty_returns_only_mappings():
    assert dict_or_empty({"a": 1}) == {"a": 1}
    assert dict_or_empty(None) == {}
    assert dict_or_empty(["x"]) == {}


def test_first_dict_returns_first_mapping_or_empty():
    assert first_dict(None, {"a": 1}, {"b": 2}) == {"a": 1}
    assert first_dict(None, [], "x") == {}


def test_unique_by_key_deduplicates_by_derived_marker():
    items = [{"id": "a"}, {"id": "b"}, {"id": "a"}, {"id": ""}, {"id": "c"}]
    assert unique_by_key(items, lambda item: item["id"]) == [{"id": "a"}, {"id": "b"}, {"id": "c"}]
