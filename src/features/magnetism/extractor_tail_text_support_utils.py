"""Utility helpers for Magnetism text-tail extraction support."""

from __future__ import annotations

from typing import Any

from src.reports.vertical_signals import vertical_preferred_terms, vertical_terms_for_text

from .extractor_data import LAYER_DEFINITIONS


def evidence_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value:
        return [str(value).strip()]
    return []


def infer_brand_name(url_str: str) -> str:
    if not url_str:
        return "Manual Upload Brand"
    from urllib.parse import urlparse

    parsed = urlparse(url_str if "://" in url_str else f"https://{url_str}")
    host = parsed.netloc or parsed.path
    if host.startswith("www."):
        host = host[4:]
    return host.split(".")[0].capitalize()


def sentences_from_text(text: str) -> list[str]:
    import re

    raw_segments = [s.strip() for s in re.split(r"[.!?\n]+", text or "") if len(s.strip()) > 5]
    segments: list[str] = []
    for segment in raw_segments:
        if len(segment) <= 320:
            segments.append(segment)
            continue
        cuts = re.split(
            r"(?=\b(?:Macroalgas|Soluciones|Únete|Unete|Ingredientes|Creamos|Servicios|Nuestras)\b)",
            segment,
        )
        segments.extend(cut.strip() for cut in cuts if len(cut.strip()) > 10)
    return segments


def is_navigation_noise(value: str) -> bool:
    low = value.lower().strip()
    if low.startswith("main menu"):
        return True
    nav_tokens = ("contacto", "contáctanos", "menu", "menú", "alternar menú")
    return len(value) < 120 and sum(1 for token in nav_tokens if token in low) >= 2


def first_matching_sentence(sentences: list[str], keywords: list[str]) -> str | None:
    for keyword in keywords:
        for sentence in sentences:
            if is_navigation_noise(sentence):
                continue
            low = sentence.lower()
            if contains_keyword(low, keyword):
                return trim_evidence(sentence, keyword)
    return None


def heuristic_finding(layer: str, evidence: str) -> str:
    description = LAYER_DEFINITIONS[layer]["description"]
    return f"Detected {description}: {evidence[:180]}"


def tldr_content_from_layer(layer: dict[str, Any]) -> str | None:
    finding = clean_optional_string(layer.get("finding"))
    evidence = clean_optional_string(layer.get("evidence"))
    if finding and not finding.startswith("Detected "):
        return finding
    return evidence or finding


def contains_keyword(text: str, keyword: str) -> bool:
    import re

    escaped = re.escape(keyword.lower())
    if " " in keyword:
        return re.search(escaped, text, flags=re.IGNORECASE) is not None
    return re.search(rf"(?<![A-Za-zÀ-ÿ0-9]){escaped}(?![A-Za-zÀ-ÿ0-9])", text, flags=re.IGNORECASE) is not None


def trim_evidence(sentence: str, keyword: str, max_chars: int = 260) -> str:
    import re

    sentence = " ".join(sentence.split())
    if len(sentence) <= max_chars:
        return clean_evidence_phrase(sentence)
    match = re.search(re.escape(keyword), sentence, flags=re.IGNORECASE)
    if not match:
        return clean_evidence_phrase(sentence[:max_chars].rstrip())
    start = max(0, match.start() - 80)
    end = min(len(sentence), start + max_chars)
    trimmed = sentence[start:end].strip()
    if start > 0:
        trimmed = f"...{trimmed}"
    if end < len(sentence):
        trimmed = f"{trimmed}..."
    return clean_evidence_phrase(trimmed)


def clean_evidence_phrase(value: str) -> str:
    cleaned = " ".join(value.split()).strip(" -•*\t")
    for marker in (" Contáctanos", " Contacto", " Nuestras soluciones", " Main Menu"):
        idx = cleaned.find(marker)
        if idx > 40:
            cleaned = cleaned[:idx].strip()
    return cleaned


def normalize_evidence(value: Any) -> str | None:
    if isinstance(value, list):
        for item in value:
            cleaned = clean_optional_string(item)
            if cleaned:
                return cleaned
        return None
    return clean_optional_string(value)


def clean_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned or cleaned.lower() in {"none", "null", "no clear signal detected in the provided sources."}:
        return None
    return cleaned


def extract_three_terms(text: str, key: str) -> list[str] | None:
    preferred = {
        "attributes": [
            "regenerativo",
            "circular",
            "sostenible",
            "medio ambiente",
            "mediterráneo",
            "funcional",
            "transparente",
            "trust",
            "security",
            "seguro",
            "real-time control",
            "centralised",
            "centralized",
            "performance",
            "innovative",
            "athletic",
            "action-oriented",
            "developer-first",
            "secure",
            "pragmatic",
            "ai-native",
            "practical",
            "editorial",
            "experimental",
            *vertical_preferred_terms("attributes"),
        ],
        "values": [
            "regenerativo",
            "circular",
            "sostenibilidad",
            "medio ambiente",
            "transparencia",
            "claridad",
            "confianza",
            "trust",
            "security",
            "inspiration",
            "inspiración",
            "inclusivity",
            "innovation",
            "innovación",
            "fairness",
            "transparency",
            "customer empathy",
            "developer empathy",
            *vertical_preferred_terms("values"),
        ],
    }
    found: list[str] = []
    low = text.lower()
    if key == "attributes":
        if any(term in low for term in ("maratón", "maraton", "athlete", "athletes", "atletas")):
            found.extend(["performance", "athletic"])
        if any(term in low for term in ("devs", "developers", "builders", "ship", "deploy", "run any code")):
            found.append("developer-first")
        if any(term in low for term in ("security", "secure", "sandboxes", "isolated", "isolation", "private networking", "encryption", "untrusted code")):
            found.append("secure")
        if any(term in low for term in ("pay only", "actual usage", "based on usage", "down to the second", "waive", "refund", "unintended charges")):
            found.append("pragmatic")
        if any(term in low for term in ("custom agents", "ai agents", "artificial intelligence", "edge of ai")):
            found.extend(["ai-native", "practical"])
        if any(term in low for term in ("newsletter", "write for you", "media company", "question")):
            found.append("editorial")
        if any(term in low for term in ("incubate", "foundry", "experiment", "what comes next")):
            found.append("experimental")
        if any(term in low for term in ("innovadores", "innovative", "innovación", "innovation")):
            found.append("innovative")
        found.extend(vertical_terms_for_text(text, "attributes"))
    if key == "values":
        if any(term in low for term in ("inspirar", "inspire", "inspiration")):
            found.append("inspiration")
        if any(term in low for term in ("todo tipo de atletas", "all types of athletes")):
            found.append("inclusivity")
        if any(term in low for term in ("waive", "refund", "unintended charges", "unexpected", "weird on your bill")):
            found.append("fairness")
        if any(term in low for term in ("based on usage", "pay only", "actual cpu", "actual usage", "billing", "down to the second")):
            found.append("transparency")
        if any(term in low for term in ("tell us", "we would love to work with you", "we have engineers", "support customers", "devs", "developers")):
            found.append("developer empathy")
        if any(term in low for term in ("innovadores", "innovative", "innovación", "innovation")):
            found.append("innovation")
        found.extend(vertical_terms_for_text(text, "values"))
    found = list(dict.fromkeys(found))
    if len(found) >= 3:
        return found[:3]
    for term in preferred.get(key, []):
        if term in low and term not in found:
            found.append(term)
        if len(found) == 3:
            return found

    if key in {"attributes", "values"}:
        return found[:3] if found else None

    import re

    candidates = re.split(r"[,;/]| and | y ", text)
    terms: list[str] = []
    for candidate in candidates:
        cleaned = re.sub(r"[^A-Za-zÀ-ÿ0-9 -]", "", candidate).strip().lower()
        words = [w for w in cleaned.split() if len(w) > 2]
        if not words:
            continue
        term = words[-1]
        if term not in terms:
            terms.append(term)
        if len(terms) == 3:
            break
    if len(terms) < 3 and key == "attributes":
        terms.extend([term for term in ["specific", "observable", "grounded"] if term not in terms])
    if len(terms) < 3 and key == "values":
        terms.extend([term for term in ["clarity", "proof", "consistency"] if term not in terms])
    return terms[:3] if terms else None
