# Brand Intelligence Acquisition Benchmark

This benchmark compares live acquisition probes across multiple brands.

Default cases:

- ChatGPT with Firecrawl
- ChatGPT with Playwright
- LangChain with Firecrawl
- LangChain with Playwright
- Base with Firecrawl
- Base with Playwright
- Allbirds with Firecrawl
- Allbirds with Playwright
- Headway with Firecrawl
- Headway with Playwright
- Hasura with Firecrawl
- Hasura with Playwright
- lab.naturaumana.ai with Firecrawl
- Obscure Thing with Firecrawl

Run:

```bash
./.venv/bin/python scripts/brand_intelligence_benchmark.py
```

Optional override:

```bash
./.venv/bin/python scripts/brand_intelligence_benchmark.py --cases-file examples/benchmarks/brand_intelligence_acquisition/cases.json
```
