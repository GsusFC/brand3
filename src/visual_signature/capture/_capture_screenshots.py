"""Shared models and pure helpers for the Visual Signature screenshot capture CLI."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from src.visual_signature.vision.composition import analyze_composition
from src.visual_signature.affordance_semantics import classify_affordance, classify_affordance_owner
from src.visual_signature.vision.palette_from_screenshot import extract_palette_from_screenshot
from src.visual_signature.vision.screenshot_quality import load_raster_image
from src.visual_signature.vision.viewport_obstruction import analyze_viewport_obstruction
from src.visual_signature.perception import PerceptualStateMachine

COOKIE_DISMISS_PHRASES = (
    ("accept all", "accept_all"),
    ("allow all", "allow_all"),
    ("reject all", "reject_all"),
    ("decline all", "decline_all"),
    ("i agree", "agree"),
    ("agree", "agree"),
    ("accept", "accept"),
    ("reject", "reject"),
    ("decline", "decline"),
    ("continue", "continue"),
    ("close", "close"),
    ("dismiss", "dismiss"),
    ("got it", "got_it"),
    ("ok", "ok"),
    ("aceptar todas", "accept_all"),
    ("aceptar todo", "accept_all"),
    ("aceptar", "accept"),
    ("permitir todas", "allow_all"),
    ("rechazar todas", "reject_all"),
    ("rechazar todo", "reject_all"),
    ("rechazar", "reject"),
    ("denegar", "decline"),
    ("de acuerdo", "agree"),
    ("continuar", "continue"),
    ("cerrar", "close"),
    ("entendido", "got_it"),
    ("vale", "ok"),
    ("x", "close"),
    ("×", "close"),
    ("✕", "close"),
    ("✖", "close"),
)
NEWSLETTER_DISMISS_PHRASES = (
    ("close", "close"),
    ("dismiss", "dismiss"),
    ("x", "close"),
    ("×", "close"),
    ("✕", "close"),
    ("✖", "close"),
)
COMMON_DISMISS_IGNORED_TERMS = (
    "manage choices",
    "manage preference",
    "manage preferences",
    "preferences",
    "settings",
    "customize",
    "configurar",
    "configuración",
    "configuracion",
    "preferencias",
    "ajustes",
    "personalizar",
    "subscribe",
    "sign up",
    "signup",
    "join",
    "register",
    "learn more",
)
DISMISSAL_TARGET_SELECTOR = "button, [role='button'], input[type='button'], input[type='submit'], a, [aria-label], [title], [tabindex='0']"


@dataclass(frozen=True)
class CaptureBrand:
    brand_name: str
    website_url: str
    screenshot_path: str
    capture_type: str = "viewport"


@dataclass
class CaptureResult:
    brand_name: str
    website_url: str
    screenshot_path: str
    status: str
    error: str | None = None
    source: str = "playwright"
    capture_type: str = "full_page"
    capture_variant: str = "viewport"
    clean_attempt_capture_variant: str | None = None
    raw_screenshot_path: str | None = None
    clean_attempt_screenshot_path: str | None = None
    secondary_screenshot_path: str | None = None
    secondary_capture_type: str | None = None
    page_url: str | None = None
    width: int | None = None
    height: int | None = None
    viewport_width: int | None = None
    viewport_height: int | None = None
    secondary_width: int | None = None
    secondary_height: int | None = None
    file_size_bytes: int | None = None
    secondary_file_size_bytes: int | None = None
    dismissal_attempted: bool = False
    dismissal_successful: bool = False
    dismissal_method: str | None = None
    clicked_text: str | None = None
    dismissal_eligibility: str | None = None
    dismissal_block_reason: str | None = None
    candidate_click_targets: list[dict[str, Any]] = field(default_factory=list)
    rejected_click_targets: list[dict[str, Any]] = field(default_factory=list)
    before_obstruction: dict[str, Any] | None = None
    after_obstruction: dict[str, Any] | None = None
    evidence_integrity_notes: list[str] = field(default_factory=list)
    raw_viewport_metrics: dict[str, Any] | None = None
    clean_attempt_metrics: dict[str, Any] | None = None
    perceptual_state: str | None = None
    perceptual_transitions: list[dict[str, Any]] = field(default_factory=list)
    mutation_audit: dict[str, Any] | None = None
    perceptual_state_data: dict[str, Any] | None = None
    captured_at: str | None = None


CaptureFn = Callable[..., dict[str, Any]]


def load_capture_brands(path: str | Path) -> list[CaptureBrand]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    rows = payload.get("brands") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("Capture input must be a list or an object with a 'brands' list")
    brands: list[CaptureBrand] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Row {index} must be an object")
        brand_name = str(row.get("brand_name") or row.get("brandName") or "").strip()
        website_url = str(row.get("website_url") or row.get("websiteUrl") or "").strip()
        screenshot_path = str(row.get("screenshot_path") or row.get("screenshotPath") or "").strip()
        capture_type = str(row.get("capture_type") or row.get("captureType") or "viewport").strip() or "viewport"
        if not brand_name or not website_url or not screenshot_path:
            raise ValueError(f"Row {index} must include brand_name, website_url, and screenshot_path")
        brands.append(
            CaptureBrand(
                brand_name=brand_name,
                website_url=website_url,
                screenshot_path=screenshot_path,
                capture_type=capture_type,
            )
        )
    return brands


def capture_result_to_dict(item: CaptureResult) -> dict[str, Any]:
    payload = asdict(item)
    perceptual_state_data = payload.pop("perceptual_state_data", None)
    has_state_output = bool(
        payload.get("perceptual_state")
        or payload.get("perceptual_transitions")
        or payload.get("mutation_audit") is not None
        or perceptual_state_data
    )
    if not payload.get("perceptual_state") and perceptual_state_data:
        payload["perceptual_state"] = perceptual_state_data.get("current_state")
    if not payload.get("perceptual_transitions") and perceptual_state_data:
        payload["perceptual_transitions"] = perceptual_state_data.get("transitions") or []
    if payload.get("mutation_audit") is None and perceptual_state_data:
        if perceptual_state_data.get("mutation_results"):
            payload["mutation_audit"] = perceptual_state_data.get("mutation_results")[-1].get("mutation_audit")
        else:
            payload["mutation_audit"] = None
    if not has_state_output:
        payload.pop("perceptual_state", None)
        payload.pop("perceptual_transitions", None)
        payload.pop("mutation_audit", None)
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def snapshot_for_path(path: Path, *, dom_html: str | None = None) -> dict[str, Any]:
    image = load_raster_image(str(path))
    palette = extract_palette_from_screenshot(image)
    composition = analyze_composition(image)
    obstruction = analyze_viewport_obstruction(dom_html=dom_html, viewport_image=image).to_dict()
    return {
        "metrics": {
            "viewport_whitespace_ratio": composition.whitespace_ratio,
            "viewport_visual_density": composition.visual_density,
            "viewport_composition": composition.composition_classification,
            "palette_color_count": palette.color_count,
            "palette_confidence": palette.confidence,
            "composition_confidence": composition.confidence,
        },
        "obstruction": obstruction,
    }


def coerce_dict_or_none(value: Any, *, field_name: str) -> dict[str, Any] | None:
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Field '{field_name}' must be valid JSON if provided as a string") from exc
        if parsed is None:
            return None
        if not isinstance(parsed, dict):
            raise ValueError(f"Field '{field_name}' must decode to an object")
        return parsed
    raise ValueError(f"Field '{field_name}' must be an object or JSON object string")


def coerce_transition_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            rows.append(item)
    return rows


def int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def format_percent(value: Any) -> str:
    numeric = float_or_none(value)
    if numeric is None:
        return "0.0%"
    return f"{numeric * 100:.1f}%"


def normalize_capture_type(value: Any) -> str:
    capture_type = str(value or "").strip().lower()
    if capture_type in {"viewport", "full_page"}:
        return capture_type
    return "viewport"


def derived_capture_path(path: Path, capture_type: str) -> Path:
    suffix = ".png"
    stem = path.name[:-len(suffix)] if path.name.endswith(suffix) else path.name
    return path.with_name(f"{stem}.{capture_type.replace('_', '-')}{path.suffix or '.png'}")


def severity_rank(value: str) -> int:
    order = {"none": 0, "minor": 1, "moderate": 2, "major": 3, "blocking": 4}
    return order.get(value, 0)


def normalize_label(value: str) -> str:
    return " ".join(str(value or "").lower().replace("\n", " ").split())


def should_attempt_obstruction_dismissal(obstruction: dict[str, Any] | None) -> bool:
    if not isinstance(obstruction, dict):
        return False
    if obstruction.get("present") is not True:
        return False
    if obstruction.get("type") not in {"cookie_banner", "cookie_modal", "newsletter_modal", "promo_modal"}:
        return False
    if float_or_none(obstruction.get("confidence")) is not None and float_or_none(obstruction.get("confidence")) < 0.55:
        return False
    signals = " ".join(str(item) for item in obstruction.get("signals") or []).lower()
    if any(token in signals for token in ("login", "paywall", "geo")):
        return False
    return True


def dismissal_eligibility(obstruction: dict[str, Any] | None) -> str:
    obstruction_type = str((obstruction or {}).get("type") or "none")
    if not isinstance(obstruction, dict) or obstruction.get("present") is not True:
        return "not_eligible"
    if obstruction_type in {"login_wall", "unknown_overlay"}:
        return "not_eligible"
    if obstruction_type in {"cookie_banner", "cookie_modal", "newsletter_modal", "promo_modal"}:
        return "eligible"
    return "not_eligible"


def dismissal_patterns_for_type(obstruction_type: str) -> tuple[tuple[str, str], ...]:
    if obstruction_type in {"newsletter_modal", "promo_modal"}:
        return (
            ("close", "close"),
            ("dismiss", "dismiss"),
            ("x", "close"),
            ("×", "close"),
            ("✕", "close"),
            ("✖", "close"),
        )
    if obstruction_type in {"cookie_banner", "cookie_modal"}:
        return (
            ("accept all", "accept_all"),
            ("allow all", "allow_all"),
            ("reject all", "reject_all"),
            ("decline all", "decline_all"),
            ("i agree", "agree"),
            ("agree", "agree"),
            ("accept", "accept"),
            ("reject", "reject"),
            ("decline", "decline"),
            ("continue", "continue"),
            ("close", "close"),
            ("dismiss", "dismiss"),
            ("got it", "got_it"),
            ("ok", "ok"),
            ("aceptar todas", "accept_all"),
            ("aceptar todo", "accept_all"),
            ("aceptar", "accept"),
            ("permitir todas", "allow_all"),
            ("rechazar todas", "reject_all"),
            ("rechazar todo", "reject_all"),
            ("rechazar", "reject"),
            ("denegar", "decline"),
            ("de acuerdo", "agree"),
            ("continuar", "continue"),
            ("cerrar", "close"),
            ("entendido", "got_it"),
            ("vale", "ok"),
            ("x", "close"),
            ("×", "close"),
            ("✕", "close"),
            ("✖", "close"),
        )
    return ()


def dismissal_context_type(obstruction: dict[str, Any] | None) -> str:
    obstruction_type = str((obstruction or {}).get("type") or "none")
    if obstruction_type in {"cookie_banner", "cookie_modal"}:
        return obstruction_type
    if obstruction_type in {"newsletter_modal", "promo_modal"} and has_cookie_consent_signal(obstruction):
        return "cookie_modal"
    return obstruction_type


def has_cookie_consent_signal(obstruction: dict[str, Any] | None) -> bool:
    if not isinstance(obstruction, dict):
        return False
    values: list[str] = []
    for key in ("signals", "page_level_signals", "overlay_level_signals", "visual_signals", "limitations"):
        raw_values = obstruction.get(key) or []
        if isinstance(raw_values, list):
            values.extend(str(value) for value in raw_values if value is not None)
    joined = normalize_label(" ".join(values)).replace("_", " ")
    return any(token in joined for token in ("cookie", "cookies", "consent", "privacy", "gdpr", "cmp"))


def contains_phrase(text: str, phrase: str) -> bool:
    normalized_text = normalize_label(text)
    normalized_phrase = normalize_label(phrase)
    if not normalized_text or not normalized_phrase:
        return False
    if normalized_text == normalized_phrase:
        return True
    return (
        normalized_text.startswith(f"{normalized_phrase} ")
        or normalized_text.endswith(f" {normalized_phrase}")
        or f" {normalized_phrase} " in f" {normalized_text} "
    )


def is_concise_dismissal_label(normalized: str) -> bool:
    words = [item for item in normalized.split() if item]
    return 0 < len(words) <= 6 and len(normalized) <= 80


def match_dismissal_pattern(normalized: str, patterns: tuple[tuple[str, str], ...]) -> dict[str, str] | None:
    if not is_concise_dismissal_label(normalized):
        return None
    for phrase, method in patterns:
        if contains_phrase(normalized, phrase):
            return {"phrase": phrase, "method": method}
    return None


def rejection_reason(normalized: str, obstruction_type: str) -> str | None:
    if obstruction_type in {"login_wall", "unknown_overlay"}:
        return f"obstruction_type_not_eligible:{obstruction_type}"
    if obstruction_type in {"newsletter_modal", "promo_modal"}:
        if any(term in normalized for term in ("subscribe", "sign up", "signup", "join", "register")):
            return "newsletter_call_to_action_not_safe"
        if any(term in normalized for term in ("manage choices", "manage preferences", "preferences", "settings", "customize")):
            return "manage_choices_not_safe"
        return "not_close_or_dismiss"
    if obstruction_type in {"cookie_banner", "cookie_modal"}:
        if any(term in normalized for term in ("subscribe", "sign up", "signup", "join", "register")):
            return "unsafe_subscription_action"
        if any(term in normalized for term in (
            "manage choices",
            "manage preference",
            "manage preferences",
            "preferences",
            "settings",
            "customize",
            "configurar",
            "configuración",
            "configuracion",
            "preferencias",
            "ajustes",
            "personalizar",
            "subscribe",
            "sign up",
            "signup",
            "join",
            "register",
            "learn more",
        )):
            return "manage_choices_not_safe"
        return "not_safe_cookie_action"
    return "not_relevant"


def dismissal_skip_note(obstruction: dict[str, Any] | None) -> str:
    if not isinstance(obstruction, dict):
        return "obstruction_unavailable"
    obstruction_type = str(obstruction.get("type") or "none")
    confidence = float_or_none(obstruction.get("confidence"))
    if obstruction_type in {"login_wall"}:
        return f"obstruction_type_not_eligible:{obstruction_type}"
    if obstruction_type == "unknown_overlay" and (confidence is None or confidence < 0.55):
        return "unknown_overlay_low_confidence"
    if obstruction.get("present") is not True:
        return "no_obstruction_detected"
    return "dismissal_not_safe"


def affordance_id(obstruction_type: str, normalized_label: str, index: int) -> str:
    return f"{obstruction_type or 'unknown'}:{normalized_label or 'element'}:{index}"


def split_context_tokens(value: str) -> list[str]:
    normalized = normalize_label(value).replace("_", " ")
    tokens = [item for item in normalized.split() if item]
    if not tokens and value:
        tokens = [str(value)]
    return tokens


def attribute_value(element: Any, attr: str) -> str:
    try:
        value = element.get_attribute(attr)
        if value and str(value).strip():
            return str(value).strip()
    except Exception:
        pass
    return ""


def affordance_evidence_for_element(element: Any, label: str, obstruction_type: str) -> dict[str, Any]:
    aria_label = attribute_value(element, "aria-label")
    title = attribute_value(element, "title")
    role = attribute_value(element, "role")
    normalized_label = normalize_label(label)
    svg_icon_semantics: list[str] = []
    if normalized_label in {"x", "×", "✕", "✖"} or aria_label.lower() in {"x", "close", "dismiss"} or title.lower() in {"x", "close", "dismiss"}:
        svg_icon_semantics.append("x")
    context_tokens = split_context_tokens(obstruction_type)
    return {
        "visible_text": [label] if label else [],
        "aria_labels": [aria_label] if aria_label else [],
        "titles": [title] if title else [],
        "roles": [role] if role else [],
        "svg_icon_semantics": svg_icon_semantics,
        "dom_context": context_tokens,
        "overlay_context": context_tokens,
    }


def affordance_localization_evidence_for_element(
    element: Any,
    label: str,
    obstruction: dict[str, Any] | None,
    *,
    dismissal_context_type: str | None = None,
) -> dict[str, Any]:
    obstruction_type = dismissal_context_type or str((obstruction or {}).get("type") or "none")
    base = affordance_evidence_for_element(element, label, obstruction_type)
    localization = element_localization_snapshot(element)
    localization["obstruction_context"] = localization_context_terms(obstruction)
    base.update(localization)
    return base


def localization_context_terms(obstruction: dict[str, Any] | None) -> list[str]:
    if not isinstance(obstruction, dict):
        return []
    terms: list[str] = []
    obstruction_type = str(obstruction.get("type") or "").strip()
    if obstruction_type:
        terms.append(obstruction_type)
    for key in ("signals", "page_level_signals", "overlay_level_signals", "visual_signals", "limitations"):
        values = obstruction.get(key) or []
        if not isinstance(values, list):
            continue
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                terms.append(text)
    return terms


def element_localization_snapshot(element: Any) -> dict[str, Any]:
    if not hasattr(element, "evaluate"):
        return {}
    try:
        snapshot = element.evaluate(
            """
            node => {
              const rect = node.getBoundingClientRect ? node.getBoundingClientRect() : null;
              const style = window.getComputedStyle ? window.getComputedStyle(node) : null;
              const ancestry = [];
              let current = node;
              for (let i = 0; current && i < 6; i += 1, current = current.parentElement) {
                const tag = current.tagName ? current.tagName.toLowerCase() : '';
                const className = typeof current.className === 'string' ? current.className : '';
                ancestry.push({
                  tag,
                  id: current.id || '',
                  role: current.getAttribute ? (current.getAttribute('role') || '') : '',
                  aria_modal: current.getAttribute ? (current.getAttribute('aria-modal') || '') : '',
                  aria_label: current.getAttribute ? (current.getAttribute('aria-label') || '') : '',
                  class_name: className,
                  text: (current.textContent || '').trim().slice(0, 120),
                });
              }
              const width = rect ? Math.round(rect.width || 0) : null;
              const height = rect ? Math.round(rect.height || 0) : null;
              const x = rect ? Math.round(rect.x || rect.left || 0) : null;
              const y = rect ? Math.round(rect.y || rect.top || 0) : null;
              const innerWidth = window.innerWidth || 0;
              const innerHeight = window.innerHeight || 0;
              let viewportLocation = null;
              if (rect) {
                const cx = (rect.left || 0) + ((rect.width || 0) / 2);
                const cy = (rect.top || 0) + ((rect.height || 0) / 2);
                const horizontal = cx < innerWidth * 0.33 ? 'left' : cx > innerWidth * 0.66 ? 'right' : 'center';
                const vertical = cy < innerHeight * 0.25 ? 'top' : cy > innerHeight * 0.75 ? 'bottom' : 'center';
                viewportLocation = (vertical === 'center' && horizontal === 'center') ? 'center' : `${vertical}_${horizontal}`;
                if ((rect.width || 0) >= innerWidth * 0.85 && (rect.height || 0) >= innerHeight * 0.55) {
                  viewportLocation = 'full';
                }
              }
              return {
                bounding_box: rect ? { x, y, width, height } : null,
                dom_ancestry: ancestry,
                viewport_location: viewportLocation,
                viewport_width: innerWidth,
                viewport_height: innerHeight,
                position: style ? (style.position || '') : '',
                z_index: style ? (style.zIndex || '') : '',
                aria_modal: node.getAttribute ? (node.getAttribute('aria-modal') || '') : '',
                role_hint: node.getAttribute ? (node.getAttribute('role') || '') : '',
                proximity_context: [],
              };
            }
            """
        )
    except Exception:
        return {}
    if isinstance(snapshot, dict):
        return snapshot
    return {}


def element_intersects_current_viewport(element: Any) -> bool:
    snapshot = element_localization_snapshot(element)
    bounding_box = snapshot.get("bounding_box") if isinstance(snapshot, dict) else None
    if not isinstance(bounding_box, dict):
        return True
    x = float_or_none(bounding_box.get("x"))
    y = float_or_none(bounding_box.get("y"))
    width = float_or_none(bounding_box.get("width"))
    height = float_or_none(bounding_box.get("height"))
    viewport_width = float_or_none(snapshot.get("viewport_width"))
    viewport_height = float_or_none(snapshot.get("viewport_height"))
    if None in (x, y, width, height) or viewport_width is None or viewport_height is None:
        return True
    if width <= 0 or height <= 0 or viewport_width <= 0 or viewport_height <= 0:
        return False
    return x + width > 0 and y + height > 0 and x < viewport_width and y < viewport_height


def element_label(element: Any) -> str:
    for getter in ("inner_text", "text_content"):
        try:
            value = getattr(element, getter)()
            if value and str(value).strip():
                return str(value).strip()
        except Exception:
            pass
    for attr in ("aria-label", "title", "value"):
        try:
            value = element.get_attribute(attr)
            if value and str(value).strip():
                return str(value).strip()
        except Exception:
            pass
    return ""


def find_dismissal_candidate(page: Any) -> dict[str, Any] | None:
    try:
        handles = page.locator("button, [role='button'], input[type='button'], input[type='submit']")
    except Exception:
        return None

    patterns = [
        ("accept all", "accept_all"),
        ("reject all", "reject_all"),
        ("continue", "continue"),
        ("close", "close"),
        ("manage choices", "manage_choices"),
    ]
    count = handles.count()
    candidates: list[dict[str, Any]] = []
    for idx in range(count):
        element = handles.nth(idx)
        try:
            if not element.is_visible():
                continue
            if not element_intersects_current_viewport(element):
                continue
            label = element_label(element)
        except Exception:
            continue
        normalized = normalize_label(label)
        if not normalized:
            continue
        if "manage choices" in normalized and count > 6:
            continue
        for needle, method in patterns:
            if needle in normalized:
                candidates.append(
                    {
                        "element": element,
                        "clicked_text": label,
                        "method": method,
                        "rank": patterns.index((needle, method)),
                    }
                )
                break
    if not candidates:
        return None
    candidates.sort(key=lambda item: item["rank"])
    return candidates[0]


def attempt_obstruction_dismissal(page: Any, obstruction: dict[str, Any] | None) -> dict[str, Any]:
    discovery = discover_dismissal_targets(page, obstruction)
    return attempt_obstruction_dismissal_with_discovery(page, obstruction, discovery)


def attempt_obstruction_dismissal_with_discovery(
    page: Any,
    obstruction: dict[str, Any] | None,
    discovery: dict[str, Any],
) -> dict[str, Any]:
    if not discovery["eligible"]:
        return {
            "attempted": False,
            "successful": False,
            "method": None,
            "clicked_text": None,
            "note": discovery["block_reason"] or dismissal_skip_note(obstruction),
            "dismissal_eligibility": discovery["dismissal_eligibility"],
            "dismissal_block_reason": discovery["block_reason"],
            "candidate_click_targets": discovery["candidate_click_targets"],
            "rejected_click_targets": discovery["rejected_click_targets"],
        }

    candidate = discovery["selected_candidate"]
    if candidate is None:
        return {
            "attempted": False,
            "successful": False,
            "method": None,
            "clicked_text": None,
            "note": discovery["block_reason"] or "no_safe_cookie_button_found",
            "dismissal_eligibility": discovery["dismissal_eligibility"],
            "dismissal_block_reason": discovery["block_reason"] or "no_safe_cookie_button_found",
            "candidate_click_targets": discovery["candidate_click_targets"],
            "rejected_click_targets": discovery["rejected_click_targets"],
        }

    try:
        candidate["element"].click(timeout=2500)
        return {
            "attempted": True,
            "successful": False,
            "method": candidate["method"],
            "clicked_text": candidate["clicked_text"],
            "note": "safe_dismissal_button_clicked",
            "dismissal_eligibility": discovery["dismissal_eligibility"],
            "dismissal_block_reason": None,
            "candidate_click_targets": discovery["candidate_click_targets"],
            "rejected_click_targets": discovery["rejected_click_targets"],
        }
    except Exception as exc:
        return {
            "attempted": True,
            "successful": False,
            "method": None,
            "clicked_text": candidate["clicked_text"],
            "note": f"dismissal_click_failed: {exc}",
            "dismissal_eligibility": discovery["dismissal_eligibility"],
            "dismissal_block_reason": "click_failed",
            "candidate_click_targets": discovery["candidate_click_targets"],
            "rejected_click_targets": discovery["rejected_click_targets"],
        }


def prepare_perceptual_state_machine(
    *,
    page: Any,
    raw_snapshot: dict[str, Any],
    raw_artifact_ref: str,
    attempt_dismiss_obstructions: bool,
) -> dict[str, Any] | None:
    if not attempt_dismiss_obstructions:
        return None

    obstruction = raw_snapshot.get("obstruction") if isinstance(raw_snapshot, dict) else None
    machine = PerceptualStateMachine.from_raw_capture(
        evidence_refs=[raw_artifact_ref],
        notes=["raw_viewport_preserved_as_primary_evidence"],
    )
    machine.classify_obstruction(
        obstruction if isinstance(obstruction, dict) else None,
        evidence_refs=[raw_artifact_ref],
    )

    if not isinstance(obstruction, dict) or obstruction.get("present") is not True:
        return {"machine": machine, "discovery": None, "eligibility": None}
    if machine.current_state == "UNSAFE_MUTATION_BLOCKED" or str(obstruction.get("type") or "") == "unknown_overlay":
        return {"machine": machine, "discovery": None, "eligibility": machine.current_state}

    discovery = discover_dismissal_targets(page, obstruction)
    affordance_labels = [str(item.get("label") or "") for item in discovery.get("candidate_click_targets") or [] if isinstance(item, dict)]
    eligibility = machine.evaluate_eligibility(
        obstruction,
        affordance_labels=affordance_labels,
        evidence_refs=[raw_artifact_ref],
    )
    return {"machine": machine, "discovery": discovery, "eligibility": eligibility}


def discover_dismissal_targets(page: Any, obstruction: dict[str, Any] | None) -> dict[str, Any]:
    obstruction_type = str((obstruction or {}).get("type") or "none")
    context_type = dismissal_context_type(obstruction)
    eligibility = dismissal_eligibility(obstruction)
    candidate_click_targets: list[dict[str, Any]] = []
    rejected_click_targets: list[dict[str, Any]] = []
    block_reason = None
    selected_candidate = None

    try:
        handles = page.locator(DISMISSAL_TARGET_SELECTOR)
        count = handles.count()
    except Exception as exc:
        return {
            "eligible": False,
            "dismissal_eligibility": "not_evaluated",
            "block_reason": f"selector_unavailable:{exc}",
            "candidate_click_targets": [],
            "rejected_click_targets": [],
            "selected_candidate": None,
        }

    patterns = dismissal_patterns_for_type(context_type)
    for idx in range(count):
        element = handles.nth(idx)
        try:
            if not element.is_visible():
                continue
            if not element_intersects_current_viewport(element):
                continue
        except Exception:
            continue

        label = element_label(element)
        normalized = normalize_label(label)
        if not normalized:
            continue
        affordance_evidence = affordance_evidence_for_element(element, label, context_type)
        localization_evidence = affordance_localization_evidence_for_element(element, label, obstruction, dismissal_context_type=context_type)
        affordance = classify_affordance(
            affordance_evidence,
            affordance_id=affordance_id(obstruction_type, normalized, idx),
        )
        localization = classify_affordance_owner(
            localization_evidence,
            affordance_id=f"{affordance_id(obstruction_type, normalized, idx)}:owner",
            affordance_category=affordance.category,
            interaction_policy=affordance.policy,
        )
        reason = rejection_reason(normalized, context_type)
        match = match_dismissal_pattern(normalized, patterns)
        is_safe_candidate = match is not None and is_safe_dismissal_candidate_fields(
            affordance_policy=affordance.policy,
            affordance_owner=localization.owner,
        )
        record = {
            "label": label,
            "normalized_label": normalized,
            "method": match["method"] if match else None,
            "selector": DISMISSAL_TARGET_SELECTOR,
            "reason": None if is_safe_candidate else (reason or ("unsafe_dismissal_candidate" if match else "not_exact_match")),
            "affordance_category": affordance.category,
            "interaction_policy": affordance.policy,
            "affordance_confidence": affordance.confidence,
            "affordance_evidence": affordance.evidence.to_dict(),
            "affordance_owner": localization.owner,
            "owner_confidence": localization.owner_confidence,
            "owner_evidence": localization.owner_evidence,
            "owner_limitations": localization.owner_limitations,
        }
        if is_safe_candidate:
            candidate_click_targets.append(record)
            if selected_candidate is None:
                selected_candidate = {
                    "element": element,
                    "clicked_text": label,
                    "method": match["method"],
                    "label": label,
                    "affordance_category": affordance.category,
                    "interaction_policy": affordance.policy,
                    "affordance_confidence": affordance.confidence,
                    "affordance_evidence": affordance.evidence.to_dict(),
                    "affordance_owner": localization.owner,
                    "owner_confidence": localization.owner_confidence,
                    "owner_evidence": localization.owner_evidence,
                    "owner_limitations": localization.owner_limitations,
                }
        elif should_record_rejected_click_target(
            record,
            normalized_label=normalized,
            patterns=patterns,
            has_dismissal_match=match is not None,
        ):
            rejected_click_targets.append(record)

    if eligibility != "eligible":
        block_reason = dismissal_skip_note(obstruction)
    elif selected_candidate is None:
        block_reason = "no_safe_cookie_button_found" if context_type in {"cookie_banner", "cookie_modal"} else "no_safe_close_button_found"
    return {
        "eligible": eligibility == "eligible",
        "dismissal_eligibility": eligibility,
        "block_reason": block_reason,
        "candidate_click_targets": candidate_click_targets,
        "rejected_click_targets": rejected_click_targets,
        "selected_candidate": selected_candidate,
    }


def is_safe_dismissal_candidate_fields(*, affordance_policy: str, affordance_owner: str) -> bool:
    if affordance_policy != "safe_to_dismiss":
        return False
    if affordance_owner in {
        "unrelated_chat_widget",
        "unrelated_cart_drawer",
        "header_navigation",
        "social_link",
    }:
        return False
    return True


def should_record_rejected_click_target(
    record: dict[str, Any],
    *,
    normalized_label: str,
    patterns: tuple[tuple[str, str], ...],
    has_dismissal_match: bool,
) -> bool:
    owner = str(record.get("affordance_owner") or "")
    reason = str(record.get("reason") or "")
    category = str(record.get("affordance_category") or "")
    known_unrelated_owner = owner in {
        "unrelated_chat_widget",
        "unrelated_cart_drawer",
        "header_navigation",
        "social_link",
    }
    if known_unrelated_owner and not has_dismissal_match:
        return False
    if has_dismissal_match:
        return True
    if owner == "active_obstruction":
        return True
    if category in {"ambiguous_action", "subscription_action"}:
        return True
    if reason in {
        "manage_choices_not_safe",
        "newsletter_call_to_action_not_safe",
        "unsafe_subscription_action",
    }:
        return True
    return any(contains_phrase(normalized_label, phrase) for phrase, _method in patterns)


def visible_obstruction_dom_snapshot(page: Any) -> str:
    if not hasattr(page, "evaluate"):
        try:
            return page.content()
        except Exception:
            return ""
    try:
        rows = page.evaluate(
            """
            () => {
              const selectors = [
                '[role="dialog"]',
                '[role="alertdialog"]',
                '[aria-modal="true"]',
                '[aria-label*="cookie" i]',
                '[aria-label*="consent" i]',
                '[aria-label*="privacy" i]',
                '[class*="cookie" i]',
                '[id*="cookie" i]',
                '[class*="consent" i]',
                '[id*="consent" i]',
                '[class*="modal" i]',
                '[id*="modal" i]',
                '[class*="popup" i]',
                '[id*="popup" i]',
                '[class*="newsletter" i]',
                '[id*="newsletter" i]',
                '[class*="banner" i]',
                '[id*="banner" i]'
              ].join(',');
              const nodes = Array.from(document.querySelectorAll(selectors));
              const candidates = [];
              const seen = new Set();
              for (const node of nodes) {
                if (!node || seen.has(node)) continue;
                seen.add(node);
                const rect = node.getBoundingClientRect ? node.getBoundingClientRect() : null;
                const style = window.getComputedStyle ? window.getComputedStyle(node) : null;
                if (!rect || !style) continue;
                const visible = rect.width > 0 && rect.height > 0
                  && rect.bottom > 0 && rect.right > 0
                  && rect.top < (window.innerHeight || 0)
                  && rect.left < (window.innerWidth || 0)
                  && style.display !== 'none'
                  && style.visibility !== 'hidden'
                  && Number(style.opacity || '1') > 0.02;
                if (!visible) continue;
                const position = style.position || '';
                const zIndex = style.zIndex || '';
                const role = node.getAttribute ? (node.getAttribute('role') || '') : '';
                const ariaModal = node.getAttribute ? (node.getAttribute('aria-modal') || '') : '';
                const ariaLabel = node.getAttribute ? (node.getAttribute('aria-label') || '') : '';
                const className = typeof node.className === 'string' ? node.className : '';
                const id = node.id || '';
                const text = (node.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 600);
                const overlayish = ['fixed', 'sticky'].includes(position)
                  || role === 'dialog'
                  || role === 'alertdialog'
                  || ariaModal === 'true'
                  || /cookie|consent|privacy|modal|popup|newsletter|banner/i.test(`${id} ${className} ${ariaLabel} ${text}`)
                  || Number.parseInt(zIndex || '0', 10) >= 100;
                if (!overlayish) continue;
                candidates.push({
                  tag: node.tagName ? node.tagName.toLowerCase() : '',
                  id,
                  className,
                  role,
                  ariaModal,
                  ariaLabel,
                  position,
                  zIndex,
                  width: Math.round(rect.width || 0),
                  height: Math.round(rect.height || 0),
                  top: Math.round(rect.top || 0),
                  left: Math.round(rect.left || 0),
                  text
                });
              }
              return candidates.slice(0, 24);
            }
            """
        )
    except Exception:
        try:
            return page.content()
        except Exception:
            return ""
    if not isinstance(rows, list):
        return ""
    parts: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        attrs = " ".join(
            f"{key}={value}"
            for key, value in {
                "tag": row.get("tag"),
                "id": row.get("id"),
                "class": row.get("className"),
                "role": row.get("role"),
                "aria-modal": row.get("ariaModal"),
                "aria-label": row.get("ariaLabel"),
                "position": row.get("position"),
                "z-index": row.get("zIndex"),
                "width": row.get("width"),
                "height": row.get("height"),
                "top": row.get("top"),
                "left": row.get("left"),
            }.items()
            if value not in (None, "")
        )
        text = str(row.get("text") or "")
        parts.append(f"<visible-overlay {attrs}>{text}</visible-overlay>")
    return "\n".join(parts)


def severity_distribution(rows: list[dict[str, Any]], *, key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        obstruction = row.get(key) or {}
        if not isinstance(obstruction, dict):
            continue
        severity = str(obstruction.get("severity") or "none")
        counts[severity] = counts.get(severity, 0) + 1
    return dict(sorted(counts.items()))


def string_distribution(rows: list[dict[str, Any]], *, key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "none")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def transition_reason_distribution(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        transitions = row.get("perceptual_transitions") or []
        if not isinstance(transitions, list):
            continue
        for transition in transitions:
            if not isinstance(transition, dict):
                continue
            reason = str(transition.get("reason") or "none")
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def all_diagnostic_targets(row: dict[str, Any]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for key in ("candidate_click_targets", "rejected_click_targets"):
        records = row.get(key) or []
        if not isinstance(records, list):
            continue
        for record in records:
            if isinstance(record, dict):
                targets.append(record)
    return targets


def affordance_distribution(rows: list[dict[str, Any]], *, key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for record in all_diagnostic_targets(row):
            value = str(record.get(key) or "unknown")
            counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def affordance_count(
    rows: list[dict[str, Any]],
    *,
    target_key: str | None,
    field_key: str,
    expected: str,
) -> int:
    total = 0
    for row in rows:
        if target_key is None:
            records = all_diagnostic_targets(row)
        else:
            records = row.get(target_key) or []
            if not isinstance(records, list):
                continue
        for record in records:
            if not isinstance(record, dict):
                continue
            if str(record.get(field_key) or "") == expected:
                total += 1
    return total


def target_distribution(row: dict[str, Any], *, key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in all_diagnostic_targets(row):
        value = str(record.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def material_viewport_change(before: dict[str, Any] | None, after: dict[str, Any] | None) -> bool:
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    if before.get("viewport_visual_density") != after.get("viewport_visual_density"):
        return True
    if before.get("viewport_composition") != after.get("viewport_composition"):
        return True
    if abs((float_or_none(before.get("viewport_whitespace_ratio")) or 0.0) - (float_or_none(after.get("viewport_whitespace_ratio")) or 0.0)) >= 0.08:
        return True
    if abs((float_or_none(before.get("palette_color_count")) or 0.0) - (float_or_none(after.get("palette_color_count")) or 0.0)) >= 2:
        return True
    return False


def clean_attempt_quality_distribution(rows: list[dict[str, Any]], *, clean_attempt_quality: Callable[[dict[str, Any]], str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        quality = clean_attempt_quality(row)
        counts[quality] = counts.get(quality, 0) + 1
    return dict(sorted(counts.items()))


def dismissal_successful(before: dict[str, Any] | None, after: dict[str, Any] | None) -> bool:
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    if not before.get("present") and not after.get("present"):
        return False
    if before.get("present") and not after.get("present"):
        return True
    severity_before = severity_rank(str(before.get("severity") or "none"))
    severity_after = severity_rank(str(after.get("severity") or "none"))
    if severity_after < severity_before:
        return True
    coverage_before = float_or_none(before.get("coverage_ratio")) or 0.0
    coverage_after = float_or_none(after.get("coverage_ratio")) or 0.0
    return coverage_after + 0.05 < coverage_before


def build_dismissal_audit(
    manifest: dict[str, Any],
    *,
    clean_attempt_quality: Callable[[dict[str, Any]], str],
) -> dict[str, Any]:
    rows = [row for row in manifest.get("results") or [] if isinstance(row, dict)]
    attempted = [row for row in rows if row.get("dismissal_attempted")]
    successful = [row for row in attempted if row.get("dismissal_successful")]
    failed = [row for row in attempted if not row.get("dismissal_successful")]
    eligibility_distribution = string_distribution(rows, key="dismissal_eligibility")
    block_reason_distribution = string_distribution(rows, key="dismissal_block_reason")
    state_distribution = string_distribution(rows, key="perceptual_state")
    transition_distribution = transition_reason_distribution(rows)
    affordance_category_distribution = affordance_distribution(rows, key="affordance_category")
    interaction_policy_distribution = affordance_distribution(rows, key="interaction_policy")
    affordance_owner_distribution = affordance_distribution(rows, key="affordance_owner")
    safe_to_dismiss_candidates_not_clicked = affordance_count(
        rows,
        target_key="rejected_click_targets",
        field_key="interaction_policy",
        expected="safe_to_dismiss",
    )
    unsafe_to_mutate_candidates_encountered = affordance_count(
        rows,
        target_key=None,
        field_key="interaction_policy",
        expected="unsafe_to_mutate",
    )
    requires_human_review_candidates_encountered = affordance_count(
        rows,
        target_key=None,
        field_key="interaction_policy",
        expected="requires_human_review",
    )
    materially_changed_cases = [row for row in attempted if material_viewport_change(row.get("raw_viewport_metrics"), row.get("clean_attempt_metrics"))]
    clean_quality_distribution = clean_attempt_quality_distribution(attempted, clean_attempt_quality=clean_attempt_quality)
    return {
        "schema_version": "visual-signature-dismissal-audit-1",
        "generated_at": datetime.now().isoformat(),
        "total_results": len(rows),
        "attempted": len(attempted),
        "successful": len(successful),
        "failed": len(failed),
        "dismissal_success_rate": rate(len(successful), len(attempted)),
        "mutation_summary": {
            "attempted": len(attempted),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": rate(len(successful), len(attempted)),
        },
        "failed_dismissals": [
            {
                "brand_name": row.get("brand_name"),
                "website_url": row.get("website_url"),
                "dismissal_method": row.get("dismissal_method"),
                "clicked_text": row.get("clicked_text"),
                "before_severity": (row.get("before_obstruction") or {}).get("severity"),
                "after_severity": (row.get("after_obstruction") or {}).get("severity"),
                "notes": row.get("evidence_integrity_notes") or [],
            }
            for row in failed
        ],
        "materially_changed_cases": [
            {
                "brand_name": row.get("brand_name"),
                "website_url": row.get("website_url"),
                "clean_attempt_quality": clean_attempt_quality(row),
                "before": row.get("raw_viewport_metrics"),
                "after": row.get("clean_attempt_metrics"),
                "before_obstruction": row.get("before_obstruction"),
                "after_obstruction": row.get("after_obstruction"),
            }
            for row in materially_changed_cases
        ],
        "before_severity_distribution": severity_distribution(rows, key="before_obstruction"),
        "after_severity_distribution": severity_distribution(rows, key="after_obstruction"),
        "eligibility_distribution": eligibility_distribution,
        "block_reason_distribution": block_reason_distribution,
        "state_distribution": state_distribution,
        "transition_reason_distribution": transition_distribution,
        "clean_attempt_quality_distribution": clean_quality_distribution,
        "affordance_category_distribution": affordance_category_distribution,
        "interaction_policy_distribution": interaction_policy_distribution,
        "affordance_owner_distribution": affordance_owner_distribution,
        "safe_to_dismiss_candidates_not_clicked": safe_to_dismiss_candidates_not_clicked,
        "unsafe_to_mutate_candidates_encountered": unsafe_to_mutate_candidates_encountered,
        "requires_human_review_candidates_encountered": requires_human_review_candidates_encountered,
        "results": [
            {
                "brand_name": row.get("brand_name"),
                "website_url": row.get("website_url"),
                "dismissal_attempted": bool(row.get("dismissal_attempted")),
                "dismissal_successful": bool(row.get("dismissal_successful")),
                "dismissal_method": row.get("dismissal_method"),
                "clicked_text": row.get("clicked_text"),
                "dismissal_eligibility": row.get("dismissal_eligibility"),
                "dismissal_block_reason": row.get("dismissal_block_reason"),
                "candidate_click_targets": row.get("candidate_click_targets") or [],
                "rejected_click_targets": row.get("rejected_click_targets") or [],
                "affordance_category_distribution": target_distribution(row, key="affordance_category"),
                "interaction_policy_distribution": target_distribution(row, key="interaction_policy"),
                "affordance_owner_distribution": target_distribution(row, key="affordance_owner"),
                "capture_variant": row.get("capture_variant"),
                "clean_attempt_capture_variant": row.get("clean_attempt_capture_variant"),
                "clean_attempt_quality": clean_attempt_quality(row),
                "raw_screenshot_path": row.get("raw_screenshot_path"),
                "clean_attempt_screenshot_path": row.get("clean_attempt_screenshot_path"),
                "perceptual_state": row.get("perceptual_state"),
                "perceptual_transitions": row.get("perceptual_transitions") or [],
                "mutation_audit": row.get("mutation_audit"),
            }
            for row in rows
        ],
    }


def dismissal_audit_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Visual Signature Dismissal Audit",
        "",
        "Evidence-quality diagnostics only. Raw viewport remains the primary evidence.",
        "",
        f"- Total results: {audit.get('total_results', 0)}",
        f"- Dismissal attempts: {audit.get('attempted', 0)}",
        f"- Successful dismissals: {audit.get('successful', 0)}",
        f"- Failed dismissals: {audit.get('failed', 0)}",
        f"- Dismissal success rate: {format_percent(audit.get('dismissal_success_rate'))}",
        f"- Mutation summary: {json.dumps(audit.get('mutation_summary') or {}, sort_keys=True)}",
        "",
        "## Severity Transitions",
        "",
        f"- Before: {json.dumps(audit.get('before_severity_distribution') or {}, sort_keys=True)}",
        f"- After: {json.dumps(audit.get('after_severity_distribution') or {}, sort_keys=True)}",
        f"- Eligibility: {json.dumps(audit.get('eligibility_distribution') or {}, sort_keys=True)}",
        f"- Block reasons: {json.dumps(audit.get('block_reason_distribution') or {}, sort_keys=True)}",
        f"- Perceptual states: {json.dumps(audit.get('state_distribution') or {}, sort_keys=True)}",
        f"- Transition reasons: {json.dumps(audit.get('transition_reason_distribution') or {}, sort_keys=True)}",
        f"- Clean attempt quality: {json.dumps(audit.get('clean_attempt_quality_distribution') or {}, sort_keys=True)}",
        f"- Affordance categories: {json.dumps(audit.get('affordance_category_distribution') or {}, sort_keys=True)}",
        f"- Interaction policies: {json.dumps(audit.get('interaction_policy_distribution') or {}, sort_keys=True)}",
        f"- Affordance owners: {json.dumps(audit.get('affordance_owner_distribution') or {}, sort_keys=True)}",
        f"- Safe-to-dismiss candidates not clicked: {audit.get('safe_to_dismiss_candidates_not_clicked', 0)}",
        f"- Unsafe-to-mutate candidates encountered: {audit.get('unsafe_to_mutate_candidates_encountered', 0)}",
        f"- Requires-human-review candidates encountered: {audit.get('requires_human_review_candidates_encountered', 0)}",
        "",
        "## Material Viewport Changes",
        "",
    ]
    changed = audit.get("materially_changed_cases") or []
    if not changed:
        lines.append("- None")
    else:
        for row in changed:
            lines.append(f"- {row.get('brand_name')} ({row.get('website_url')})")
    lines.extend(["", "## Failed Dismissals", "", "| Brand | Method | Clicked Text | Before | After |", "| --- | --- | --- | --- | --- |"])
    failed = audit.get("failed_dismissals") or []
    if not failed:
        lines.append("| - | - | - | - | - |")
    else:
        for row in failed:
            lines.append(
                f"| {row.get('brand_name')} | {row.get('dismissal_method') or '-'} | {row.get('clicked_text') or '-'} | "
                f"{row.get('before_severity') or '-'} | {row.get('after_severity') or '-'} |"
            )
    return "\n".join(lines)
