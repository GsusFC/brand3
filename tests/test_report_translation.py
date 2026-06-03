from src.reports.translation import (
    translate_executive_analysis_v2,
    translate_report_narrative_payload,
)


class FakeTranslator:
    def __init__(self):
        self.calls = []

    def _call_json(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "synthesis_prose": "Síntesis traducida.",
            "summary": "Síntesis traducida.",
            "tensions_prose": "Tensión traducida.",
            "findings_by_dimension": {
                "coherencia": [
                    {
                        "title": "Título traducido",
                        "observation": "Observación traducida.",
                        "implication": "Implicación traducida.",
                        "typical_decision": "Decisión traducida.",
                        "evidence_urls": ["https://should-not-win.example"],
                    }
                ]
            },
        }


def test_translate_report_narrative_payload_preserves_evidence_urls():
    source = {
        "version": 1,
        "source": "report_narrative",
        "run_id": 123,
        "synthesis_prose": "Original synthesis.",
        "summary": "Original synthesis.",
        "tensions_prose": "Original tension.",
        "findings_by_dimension": {
            "coherencia": [
                {
                    "title": "Original title",
                    "observation": "Original observation.",
                    "implication": "Original implication.",
                    "typical_decision": "Original decision.",
                    "evidence_urls": ["https://example.com/evidence"],
                }
            ]
        },
    }

    translated = translate_report_narrative_payload(
        source,
        target_lang="es",
        analyzer=FakeTranslator(),
    )

    assert translated is not None
    assert translated["target_lang"] == "es"
    assert translated["run_id"] == 123
    assert translated["synthesis_prose"] == "Síntesis traducida."
    finding = translated["findings_by_dimension"]["coherencia"][0]
    assert finding["title"] == "Título traducido"
    assert finding["evidence_urls"] == ["https://example.com/evidence"]


def test_translate_report_narrative_payload_returns_none_without_analyzer():
    translated = translate_report_narrative_payload(
        {"synthesis_prose": "Original.", "findings_by_dimension": {}},
        target_lang="es",
        analyzer=None,
    )

    assert translated is None


class FakeExecutiveTranslator:
    def _call_json(self, **kwargs):
        return {
            "executive_summary": "Resumen ejecutivo traducido.",
            "primary_risk": "Riesgo traducido.",
            "primary_opportunity": "Oportunidad traducida.",
            "dimensions": {
                "coherencia": {
                    "diagnosis": "Diagnóstico traducido.",
                    "findings": ["Hallazgo traducido."],
                    "evidence": ["Evidencia traducida."],
                    "recommendation": "Recomendación traducida.",
                    "confidence": "translated-should-not-win",
                }
            },
        }


def test_translate_executive_analysis_v2_preserves_dimension_keys_and_confidence():
    source = {
        "executive_summary": "Original summary.",
        "primary_risk": "Original risk.",
        "primary_opportunity": "Original opportunity.",
        "dimensions": {
            "coherencia": {
                "diagnosis": "Original diagnosis.",
                "findings": ["Original finding."],
                "evidence": ["Original evidence."],
                "recommendation": "Original recommendation.",
                "confidence": "high",
            }
        },
    }

    translated = translate_executive_analysis_v2(
        source,
        target_lang="es",
        analyzer=FakeExecutiveTranslator(),
    )

    assert translated is not None
    assert translated["target_lang"] == "es"
    assert translated["executive_summary"] == "Resumen ejecutivo traducido."
    assert set(translated["dimensions"]) == {"coherencia"}
    dimension = translated["dimensions"]["coherencia"]
    assert dimension["diagnosis"] == "Diagnóstico traducido."
    assert dimension["findings"] == ["Hallazgo traducido."]
    assert dimension["evidence"] == ["Evidencia traducida."]
    assert dimension["recommendation"] == "Recomendación traducida."
    assert dimension["confidence"] == "high"
