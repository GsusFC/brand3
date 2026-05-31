from src.reports.translation import translate_report_narrative_payload


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
