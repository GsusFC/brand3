"""Display strings and navigation helpers for the Visual Signature web lab."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any


HUMAN_REVIEW_SCRIPT_PATH = Path(__file__).resolve().parent / "static" / "visual_signature_human_review.js"

SECTION_TITLES = {
    "overview": {
        "es": "Laboratorio de Visual Signature",
        "en": "Visual Signature Lab",
    },
    "governance": {
        "es": "Gobernanza del Laboratorio de Visual Signature",
        "en": "Visual Signature Lab Governance",
    },
    "calibration": {
        "es": "Calibración del Laboratorio de Visual Signature",
        "en": "Visual Signature Lab Calibration",
    },
    "corpus": {
        "es": "Corpus del Laboratorio de Visual Signature",
        "en": "Visual Signature Lab Corpus",
    },
    "reviewer": {
        "es": "Revisor del Laboratorio de Visual Signature",
        "en": "Visual Signature Lab Reviewer",
    },
}

SECTION_INTROS = {
    "overview": {
        "es": "Navegación de solo lectura del Laboratorio de Visual Signature. La evidencia se muestra separada del scoring de Brand3 y no tiene impacto en scoring, rúbrica, reporte, proveedor o mutación en runtime.",
        "en": "Read-only Visual Signature Lab navigation. Evidence is shown separately from Brand3 Scoring and has no scoring, rubric, report, provider, or runtime mutation impact.",
    },
    "governance": {
        "es": "Registro de capacidades, matriz de políticas en runtime, integridad de gobernanza y planificación de validación del laboratorio. Solo lectura.",
        "en": "Capability registry, runtime policy matrix, governance integrity, and validation planning for the lab. Read-only.",
    },
    "calibration": {
        "es": "Manifiestos de calibración, registros, reporte de confiabilidad y estado de readiness del laboratorio. Solo lectura.",
        "en": "Calibration manifests, records, reliability report, and readiness status for the lab. Read-only.",
    },
    "corpus": {
        "es": "Manifiesto de expansión de corpus, métricas piloto, estado de cola y limitaciones del laboratorio. Solo lectura.",
        "en": "Corpus expansion manifest, pilot metrics, queue state, and limitations for the lab. Read-only.",
    },
    "reviewer": {
        "es": "Piloto de workflow de revisión, items seleccionados de la cola, enlaces a packets y punto de entrada local al viewer del revisor. Solo lectura.",
        "en": "Reviewer workflow pilot, selected queue items, packet links, and local reviewer viewer entry point. Read-only.",
    },
}

SECTION_NAV_LABELS = {
    "overview": {"es": "Resumen", "en": "Lab Overview"},
    "governance": {"es": "Gobernanza", "en": "Governance"},
    "calibration": {"es": "Calibración", "en": "Calibration"},
    "corpus": {"es": "Corpus", "en": "Corpus"},
    "reviewer": {"es": "Revisor", "en": "Reviewer"},
}

HUMAN_REVIEW_TITLE = {
    "es": "Revisión humana del Laboratorio de Visual Signature",
    "en": "Visual Signature Lab Human Review",
}

HUMAN_REVIEW_INTRO = {
    "es": "Revisión humana guiada por evidencia para el Laboratorio de Visual Signature. Los borradores son solo locales en esta fase y no crean registros de revisión completos.",
    "en": "Evidence-first human review for the Visual Signature Lab. Draft answers are local-only in this phase and do not create completed review records.",
}

HUMAN_REVIEW_GUARDRAILS = {
    "es": [
        "solo evidencia",
        "sin impacto en scoring",
        "sin persistencia",
        "sin llamadas a proveedores",
        "sin mutación en runtime",
        "sin registros de revisión completos",
    ],
    "en": [
        "evidence-only",
        "no scoring impact",
        "no persistence",
        "no provider calls",
        "no runtime mutation",
        "no completed review records",
    ],
}

HUMAN_REVIEW_BANNER = {
    "es": {
        "title": "Usa solo evidencia visible.",
        "copy": "Esta pantalla no escribe registros de revisión, no afecta a Brand3 Scoring y no llama a proveedores.",
    },
    "en": {
        "title": "Use visible evidence only.",
        "copy": "This screen does not write review records, does not affect Brand3 Scoring, and does not call providers.",
    },
}


def visual_signature_human_review_script_version() -> str:
    try:
        return sha256(HUMAN_REVIEW_SCRIPT_PATH.read_bytes()).hexdigest()[:12]
    except OSError:
        return "dev"


def visual_signature_nav(lang: str, *, active_section: str) -> list[dict[str, Any]]:
    if lang not in ("es", "en"):
        lang = "es"
    return [
        {"label": SECTION_NAV_LABELS["overview"][lang], "href": "/visual-signature", "active": active_section == "overview"},
        {"label": SECTION_NAV_LABELS["governance"][lang], "href": "/visual-signature/governance", "active": active_section == "governance"},
        {"label": SECTION_NAV_LABELS["calibration"][lang], "href": "/visual-signature/calibration", "active": active_section == "calibration"},
        {"label": SECTION_NAV_LABELS["corpus"][lang], "href": "/visual-signature/corpus", "active": active_section == "corpus"},
        {"label": SECTION_NAV_LABELS["reviewer"][lang], "href": "/visual-signature/reviewer", "active": active_section == "reviewer"},
    ]


def visual_signature_guardrails(lang: str) -> list[str]:
    if lang not in ("es", "en"):
        lang = "es"
    if lang == "en":
        return [
            "evidence-only",
            "no scoring impact",
            "no rubric impact",
            "no production report impact",
            "no provider calls",
            "no runtime mutation",
            "read-only source artifact navigation",
        ]
    return [
        "solo evidencia",
        "sin impacto en scoring",
        "sin impacto en rúbrica",
        "sin impacto en reportes de producción",
        "sin llamadas a proveedores",
        "sin mutación en runtime",
        "navegación de artefactos fuente en solo lectura",
    ]


def visual_signature_next_steps(section: str, lang: str) -> list[str]:
    if lang not in ("es", "en"):
        lang = "es"
    if section == "overview":
        if lang == "en":
            return [
                "Use Brand3 Scoring through the existing scan form and report routes.",
                "Use Visual Signature pages only to inspect source artifacts and readiness.",
                "Keep scoring and Visual Signature decisions separate.",
            ]
        return [
            "Usa Brand3 Scoring a través del formulario de escaneo y las rutas de reporte existentes.",
            "Usa las páginas de Visual Signature solo para inspeccionar artefactos fuente y readiness.",
            "Mantén separadas las decisiones de scoring y Visual Signature.",
        ]
    if section == "governance":
        return [
            "Resolve governance integrity errors in source artifacts before expanding runtime scope."
            if lang == "en"
            else "Resuelve los errores de integridad de gobernanza en los artefactos fuente antes de ampliar el alcance en runtime."
        ]
    if section == "calibration":
        return [
            "Use calibration readiness block reasons to decide the next evidence target."
            if lang == "en"
            else "Usa los motivos de bloqueo de calibration readiness para decidir el siguiente objetivo de evidencia."
        ]
    if section == "corpus":
        return [
            "Review pilot metrics and queue state before broadening corpus expansion."
            if lang == "en"
            else "Revisa las métricas del piloto y el estado de la cola antes de ampliar corpus."
        ]
    if section == "reviewer":
        return [
            "Open reviewer packets/viewer for human review, but do not persist decisions through this platform."
            if lang == "en"
            else "Abre los packets/viewer del revisor para la revisión humana, pero no persistas decisiones a través de esta plataforma."
        ]
    return []
