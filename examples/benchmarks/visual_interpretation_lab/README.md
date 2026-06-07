# Visual Interpretation Lab Benchmark

Benchmark Lab-only para evaluar si una lectura multimodal con Gemini aporta más valor que las heurísticas de Visual Diagnosis.

Uso seco, sin red ni coste:

```bash
./.venv/bin/python scripts/visual_interpretation_lab.py \
  --manifest examples/benchmarks/visual_interpretation_lab/cases.json
```

Uso real con Gemini:

```bash
BRAND3_LLM_API_KEY=... ./.venv/bin/python scripts/visual_interpretation_lab.py \
  --manifest examples/benchmarks/visual_interpretation_lab/cases.json \
  --execute \
  --model gemini-2.5-flash \
  --adjudicate \
  --adjudicator-model gemini-2.5-pro
```

Regla de integración: estos resultados no alimentan Brand Audit, Scanner, scoring ni reportes productivos. Solo sirven para decidir si Visual Signature debe evolucionar hacia una interpretación multimodal gobernada.
