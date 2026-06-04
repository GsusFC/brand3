# Search Enrichment Lab Benchmark

Small online benchmark set for `scripts/search_enrichment_lab.py`.

The cases are intentionally mixed:

- company brand
- product with parent brand
- ecosystem/protocol
- small or less-known brand
- ambiguous URL/name fit

Run a low-cost smoke:

```bash
./.venv/bin/python scripts/search_enrichment_lab.py \
  --cases-file examples/benchmarks/search_enrichment_lab/cases.json \
  --results 1 \
  --max-cases 1 \
  --max-queries 1
```

Run a broader Lab pass only when provider cost is acceptable:

```bash
./.venv/bin/python scripts/search_enrichment_lab.py \
  --cases-file examples/benchmarks/search_enrichment_lab/cases.json \
  --results 2 \
  --max-queries 3
```

Outputs are written to `out/search_enrichment_lab/<timestamp>/`.

