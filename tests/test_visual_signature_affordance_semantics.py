from __future__ import annotations

from src.visual_signature.affordance_semantics import (
    build_affordance_export,
    classify_affordance,
    export_affordance_json,
)


def test_exact_close_button_is_safe_to_dismiss():
    result = classify_affordance(
        {
            "visible_text": ["Close"],
            "roles": ["button"],
            "dom_context": ["modal"],
        }
    )

    assert result.category == "close_control"
    assert result.policy == "safe_to_dismiss"
    assert result.review_required is False
    assert "text_or_context:close" in result.matched_signals


def test_aria_label_close_icon_is_close_control():
    result = classify_affordance(
        {
            "aria_labels": ["Close dialog"],
            "roles": ["button"],
            "overlay_context": ["newsletter_modal"],
        }
    )

    assert result.category == "close_control"
    assert result.policy == "safe_to_dismiss"
    assert "aria_or_title:close_or_dismiss" in result.matched_signals


def test_svg_x_dismiss_icon_is_dismiss_control():
    result = classify_affordance(
        {
            "svg_icon_semantics": ["x"],
            "roles": ["button"],
            "overlay_context": ["cookie_modal"],
        }
    )

    assert result.category == "dismiss_control"
    assert result.policy == "safe_to_dismiss"
    assert "svg_icon_semantics:close_or_dismiss" in result.matched_signals


def test_subscribe_button_is_subscription_action():
    result = classify_affordance(
        {
            "visible_text": ["Subscribe"],
            "roles": ["button"],
            "dom_context": ["newsletter"],
        }
    )

    assert result.category == "subscription_action"
    assert result.policy == "unsafe_to_mutate"
    assert "text_or_context:subscription" in result.matched_signals


def test_continue_to_checkout_is_checkout_action():
    result = classify_affordance(
        {
            "visible_text": ["Continue to checkout"],
            "roles": ["button"],
            "dom_context": ["checkout"],
        }
    )

    assert result.category == "checkout_action"
    assert result.policy == "unsafe_to_mutate"
    assert "text_or_context:checkout" in result.matched_signals


def test_continue_inside_cookie_modal_is_consent_accept():
    result = classify_affordance(
        {
            "visible_text": ["Continue"],
            "roles": ["button"],
            "overlay_context": ["cookie_modal"],
            "dom_context": ["cookie", "consent"],
        }
    )

    assert result.category == "consent_accept"
    assert result.policy == "safe_to_dismiss"
    assert result.review_required is False
    assert "text:consent_accept" in result.matched_signals


def test_accept_all_cookies_is_consent_accept():
    result = classify_affordance(
        {
            "visible_text": ["Accept all cookies"],
            "roles": ["button"],
            "overlay_context": ["cookie_banner"],
            "dom_context": ["cookie", "consent"],
        }
    )

    assert result.category == "consent_accept"
    assert result.policy == "safe_to_dismiss"
    assert "text:consent_accept" in result.matched_signals


def test_ambiguous_ok_button_requires_review():
    result = classify_affordance(
        {
            "visible_text": ["OK"],
            "roles": ["button"],
        }
    )

    assert result.category == "ambiguous_action"
    assert result.policy == "requires_human_review"
    assert result.review_required is True


def test_external_navigation_cta_is_unsafe_to_mutate():
    result = classify_affordance(
        {
            "visible_text": ["Learn more"],
            "roles": ["link"],
            "svg_icon_semantics": ["external-link"],
            "dom_context": ["external_link"],
        }
    )

    assert result.category == "external_navigation"
    assert result.policy == "unsafe_to_mutate"
    assert "text_or_context:external_navigation" in result.matched_signals or "svg_icon_semantics:external_link" in result.matched_signals


def test_affordance_export_serializes_records(tmp_path):
    records = [
        classify_affordance({"visible_text": ["Close"], "roles": ["button"]}),
        classify_affordance({"visible_text": ["Subscribe"], "roles": ["button"]}),
    ]

    export = build_affordance_export(records, source="test-suite")
    assert export.schema_version == "visual-signature-affordance-export-1"
    assert export.category_counts["close_control"] == 1
    assert export.policy_counts["safe_to_dismiss"] == 1
    assert export.policy_counts["unsafe_to_mutate"] == 1

    path = tmp_path / "affordance_export.json"
    payload = export_affordance_json(path, records, source="test-suite")

    assert path.exists()
    assert payload["record_type"] == "affordance_export"
    assert len(payload["records"]) == 2
