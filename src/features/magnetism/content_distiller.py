"""Content distillation for Brand3 Magnetism evidence.

This module keeps acquisition providers separate from strategic interpretation.
It turns noisy webpage text into a smaller set of evidence candidates before TLDR
blocks try to interpret brand signals.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DistilledContent:
    source_url: str
    source_provider: str
    input_chars: int
    selected_lines: list[str] = field(default_factory=list)
    rejected_lines: list[dict[str, str]] = field(default_factory=list)
    evidence_groups: dict[str, list[str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    quality_score: int = 0

    @property
    def selected_text(self) -> str:
        return "\n".join(self.selected_lines).strip()

    def to_summary(self) -> dict[str, Any]:
        return {
            "source_url": self.source_url,
            "source_provider": self.source_provider,
            "input_chars": self.input_chars,
            "selected_chars": len(self.selected_text),
            "selected_count": len(self.selected_lines),
            "rejected_count": len(self.rejected_lines),
            "quality_score": self.quality_score,
            "warnings": self.warnings,
            "evidence_groups": self.evidence_groups,
            "selected_lines": self.selected_lines,
            "rejected_lines": self.rejected_lines[:20],
        }


class ContentDistiller:
    """Select TLDR-relevant evidence and reject common webpage noise."""

    GROUP_KEYWORDS: dict[str, tuple[str, ...]] = {
        "hero_claims": (
            "introducing",
            "meet ",
            "built for",
            "designed for",
            "purpose-built",
            "just do it",
            "financial infrastructure",
            "infraestructura financiera",
            "system for",
        ),
        "value_proposition": (
            "helps",
            "help ",
            "for teams",
            "for businesses",
            "para empresas",
            "accept payments",
            "aceptar pagos",
            "manage",
            "gestionar",
            "create models",
            "modelos de facturación",
            "product development",
            "planning and building",
            "servicios financieros",
            "revenue",
        ),
        "product_offer": (
            "platform",
            "plataforma",
            "infrastructure",
            "infraestructura",
            "api",
            "payments",
            "pagos",
            "billing",
            "facturación",
            "connect",
            "integrations",
            "services",
            "servicios",
            "products",
            "productos",
        ),
        "audience": (
            "teams",
            "agents",
            "developers",
            "businesses",
            "founders",
            "startups",
            "finance teams",
            "empresas",
            "atletas",
            "athletes",
        ),
        "proof_points": (
            "customers",
            "trusted by",
            "millions",
            "global",
            "leader",
            "forbes",
            "used by",
        ),
        "mission_language": (
            "we build",
            "we create",
            "we provide",
            "we help",
            "help companies",
            "ayuda a",
            "ofrece",
            "creamos",
            "proporcionamos",
        ),
        "vision_language": (
            "future of",
            "built for the future",
            "new model",
            "new paradigm",
            "futuro de",
            "nuevo modelo",
            "shape the future",
        ),
        "values_language": (
            "trusted",
            "secure",
            "privacy",
            "transparent",
            "sustainable",
            "regenerative",
            "confianza",
            "seguro",
            "sostenible",
        ),
        "personality_tone": (
            "bold",
            "fast",
            "simple",
            "powerful",
            "precise",
            "inspire",
            "inspirar",
            "innovative",
            "innovadores",
        ),
        "visual_or_conceptual_language": (
            "design",
            "beautiful",
            "minimal",
            "visual",
            "brand",
            "experience",
            "experiencias",
        ),
    }

    REJECTION_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
        ("technical_placeholder", re.compile(r"%[A-Z0-9_\-]+%|__NEXT_DATA__|webpack|hydration", re.I)),
        ("terminal_or_code_trace", re.compile(r"(/bin/bash|rg --files|\$ /|\b[a-z0-9_-]+/[a-z0-9_-]+\$|vehicle_state|root AGENTS file|received your request|kicked off a task)", re.I)),
        ("graphql_or_api_changelog", re.compile(r"\b(remove|removed|deprecat|changelog|release|schema|mutation|query|graphql|endpoint|contentdata)\b", re.I)),
        ("roadmap_or_docs_nav", re.compile(r"\b(product roadmap|roadmap|docs|documentation|api reference|developer docs|open app|log in|sign up)\b", re.I)),
        ("media_player_chrome", re.compile(r"\b(seek to live|currently behind live|captions settings|dialog window|escape will cancel|restore all settings|default valuesdone|beginning of dialog|opens captions settings)\b", re.I)),
        ("navigation", re.compile(r"\b(skip to content|back|sign in|start now|contact sales|pricing|resources|developers|buscar una tienda|ayuda|estado del pedido|envío|devoluciones|contacta con nosotros|omite para ir)\b", re.I)),
        ("legal_footer", re.compile(r"(©|\b(privacy policy|terms|cookie|condiciones de venta|política de privacidad|legal|accessibility|copyright|all rights reserved|todos los derechos reservados)\b)", re.I)),
        ("commerce_chrome", re.compile(r"\b(add to cart|bag|checkout|shipping|returns|size guide|favorite|wishlist|comprar|carrito)\b", re.I)),
        ("interview_or_article", re.compile(r"\b(interview|podcast|hear them discuss|blog|article|press|news|author|read more|case study|advice for founders)\b", re.I)),
    )

    def distill(self, text: str, *, source_url: str = "", source_provider: str = "unknown") -> DistilledContent:
        lines = self._candidate_lines(text)
        selected: list[tuple[int, int, str, list[str]]] = []
        rejected: list[dict[str, str]] = []
        seen: set[str] = set()

        for idx, line in enumerate(lines):
            normalized = self._normalize_line(line)
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                rejected.append({"line": normalized[:220], "reason": "duplicate"})
                continue
            seen.add(key)

            reject_reason = self._reject_reason(normalized)
            if reject_reason:
                rejected.append({"line": normalized[:220], "reason": reject_reason})
                continue

            groups = self._groups_for_line(normalized)
            score = self._score_line(normalized, groups)
            if score <= 0:
                rejected.append({"line": normalized[:220], "reason": "low_strategic_signal"})
                continue
            selected.append((score, idx, normalized, groups))

        selected.sort(key=lambda item: (-item[0], item[1]))
        top = selected[:18]
        top.sort(key=lambda item: item[1])
        selected_lines = [line for _, _, line, _ in top]

        evidence_groups: dict[str, list[str]] = {group: [] for group in self.GROUP_KEYWORDS}
        for _, _, line, groups in top:
            for group in groups:
                if len(evidence_groups[group]) < 4:
                    evidence_groups[group].append(line)
        evidence_groups = {key: value for key, value in evidence_groups.items() if value}

        warnings: list[str] = []
        if len(lines) > 80:
            warnings.append("High-volume page content was reduced before interpretation.")
        if len(selected_lines) < 3 and len(lines) >= 3:
            warnings.append("Low evidence coverage after distillation; TLDR should remain provisional.")
        if any(item["reason"] in {"graphql_or_api_changelog", "technical_placeholder"} for item in rejected):
            warnings.append("Technical/product-update noise was rejected before TLDR interpretation.")

        quality_score = self._quality_score(lines, selected_lines, evidence_groups, rejected)
        return DistilledContent(
            source_url=source_url,
            source_provider=source_provider,
            input_chars=len(text or ""),
            selected_lines=selected_lines,
            rejected_lines=rejected,
            evidence_groups=evidence_groups,
            warnings=warnings,
            quality_score=quality_score,
        )

    def _candidate_lines(self, text: str) -> list[str]:
        raw_lines: list[str] = []
        for raw in (text or "").splitlines():
            raw = self._normalize_line(raw)
            if not raw:
                continue
            if len(raw) <= 360:
                raw_lines.append(raw)
                continue
            chunks = re.split(r"(?<=[.!?])\s+|\s{2,}", raw)
            raw_lines.extend(chunk for chunk in chunks if len(chunk.strip()) >= 8)
        return raw_lines

    @staticmethod
    def _normalize_line(line: str) -> str:
        line = re.sub(r"\[[^\]]*\]\([^)]*\)", lambda m: m.group(0).split("](", 1)[0].strip("["), line or "")
        line = re.sub(r"<[^>]+>", " ", line)
        line = re.sub(r"\s+", " ", line).strip(" -|•	")
        return line.strip()

    def _reject_reason(self, line: str) -> str:
        for reason, pattern in self.REJECTION_RULES:
            if pattern.search(line):
                if reason == "navigation" and self._has_strong_brand_signal(line):
                    continue
                if reason == "graphql_or_api_changelog" and self._has_strong_value_signal(line) and "graphql" not in line.lower():
                    continue
                return reason
        if len(line) < 12:
            return "too_short"
        if len(line.split()) <= 3 and not any(term in line.lower() for term in ("just do it", "stripe", "linear", "nike", "built for the future")):
            return "too_short"
        if self._looks_like_nav_cluster(line):
            return "navigation_cluster"
        return ""

    def _groups_for_line(self, line: str) -> list[str]:
        low = line.lower()
        groups: list[str] = []
        for group, keywords in self.GROUP_KEYWORDS.items():
            if any(keyword in low for keyword in keywords):
                groups.append(group)
        return groups

    def _score_line(self, line: str, groups: list[str]) -> int:
        score = len(groups) * 2
        word_count = len(line.split())
        if 6 <= word_count <= 34:
            score += 2
        if 35 <= word_count <= 60:
            score += 1
        if line.startswith("#"):
            score += 2
        if self._has_strong_brand_signal(line):
            score += 4
        if self._has_strong_value_signal(line):
            score += 3
        if len(line) > 280:
            score -= 2
        return score

    @staticmethod
    def _has_strong_brand_signal(line: str) -> bool:
        low = line.lower()
        return any(
            term in low
            for term in (
                "financial infrastructure",
                "infraestructura financiera",
                "product development system",
                "purpose-built",
                "just do it",
                "inspirar a todo tipo de atletas",
                "built for planning",
            )
        )

    @staticmethod
    def _has_strong_value_signal(line: str) -> bool:
        low = line.lower()
        return any(
            term in low
            for term in (
                "accept payments",
                "aceptar pagos",
                "financial services",
                "servicios financieros",
                "facturación",
                "gestionar el movimiento de dinero",
                "planning and building products",
                "for teams and agents",
            )
        )

    @staticmethod
    def _looks_like_nav_cluster(line: str) -> bool:
        low = line.lower()
        nav_terms = (
            "products",
            "solutions",
            "developers",
            "resources",
            "pricing",
            "sign in",
            "contact",
            "help",
            "shipping",
            "returns",
            "search",
            "log in",
        )
        return len(line) < 180 and sum(1 for term in nav_terms if term in low) >= 4

    @staticmethod
    def _quality_score(
        all_lines: list[str],
        selected_lines: list[str],
        evidence_groups: dict[str, list[str]],
        rejected: list[dict[str, str]],
    ) -> int:
        if not all_lines:
            return 0
        score = 20
        score += min(35, len(selected_lines) * 4)
        score += min(30, len(evidence_groups) * 5)
        if len(rejected) > len(selected_lines) * 3:
            score -= 10
        if not evidence_groups.get("value_proposition") and not evidence_groups.get("product_offer"):
            score -= 20
        return max(0, min(100, score))
