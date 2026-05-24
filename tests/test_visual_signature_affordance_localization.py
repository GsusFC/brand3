from __future__ import annotations

from src.visual_signature.affordance_semantics import classify_affordance_owner


def test_close_chat_is_unrelated_chat_widget():
    result = classify_affordance_owner(
        {
            "visible_text": ["Close chat"],
            "roles": ["button"],
            "dom_context": ["chat", "widget"],
            "overlay_context": ["chat_widget"],
            "dom_ancestry": [{"tag": "div", "id": "chat-widget", "role": "complementary"}],
            "bounding_box": {"x": 1090, "y": 760, "width": 210, "height": 72},
            "viewport_location": "bottom_right",
            "position": "fixed",
            "z_index": "999",
        }
    )

    assert result.owner == "unrelated_chat_widget"
    assert result.owner_confidence >= 0.9
    assert any("chat_widget" in item or "chat" in item for item in result.owner_evidence)


def test_close_cart_is_unrelated_cart_drawer():
    result = classify_affordance_owner(
        {
            "visible_text": ["Close cart"],
            "roles": ["button"],
            "dom_context": ["cart", "drawer"],
            "overlay_context": ["cart_drawer"],
            "dom_ancestry": [{"tag": "aside", "id": "mini-cart", "role": "complementary"}],
            "bounding_box": {"x": 1040, "y": 220, "width": 320, "height": 620},
            "viewport_location": "right_center",
            "position": "fixed",
            "z_index": "1000",
        }
    )

    assert result.owner == "unrelated_cart_drawer"
    assert result.owner_confidence >= 0.9


def test_header_cta_is_header_navigation():
    result = classify_affordance_owner(
        {
            "visible_text": ["Sign up"],
            "roles": ["link"],
            "dom_context": ["header", "nav"],
            "dom_ancestry": [{"tag": "header", "id": "site-header", "role": "navigation"}],
            "bounding_box": {"x": 820, "y": 18, "width": 110, "height": 34},
            "viewport_location": "top_right",
            "position": "sticky",
            "z_index": "100",
        }
    )

    assert result.owner == "header_navigation"
    assert result.owner_confidence >= 0.85


def test_social_icon_is_social_link():
    result = classify_affordance_owner(
        {
            "visible_text": ["Twitter"],
            "roles": ["link"],
            "svg_icon_semantics": ["twitter"],
            "dom_context": ["social", "share"],
            "dom_ancestry": [{"tag": "footer", "id": "site-footer"}],
        }
    )

    assert result.owner == "social_link"
    assert result.owner_confidence >= 0.85


def test_true_modal_close_button_is_active_obstruction():
    result = classify_affordance_owner(
        {
            "visible_text": ["Close"],
            "roles": ["button"],
            "dom_context": ["cookie", "consent", "modal"],
            "overlay_context": ["cookie_modal"],
            "dom_ancestry": [
                {"tag": "div", "id": "cookie-modal", "role": "dialog", "aria_modal": "true"},
                {"tag": "button", "text": "Close"},
            ],
            "bounding_box": {"x": 760, "y": 180, "width": 280, "height": 260},
            "viewport_location": "center",
            "position": "fixed",
            "z_index": "1200",
            "aria_modal": True,
            "role_hint": "dialog",
        }
    )

    assert result.owner == "active_obstruction"
    assert result.owner_confidence >= 0.9


def test_ambiguous_close_button_is_unknown_owner():
    result = classify_affordance_owner(
        {
            "visible_text": ["Close"],
            "roles": ["button"],
        }
    )

    assert result.owner == "unknown_owner"
    assert result.owner_confidence < 0.6
