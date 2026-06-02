# Brand Intelligence Acquisition Benchmark

This benchmark compares live acquisition probes across multiple brands.

Default cases:

- ChatGPT with Firecrawl
- ChatGPT with Playwright
- ChatGPT with TinyFish
- ChatGPT with Context.dev
- LangChain with Firecrawl
- LangChain with Playwright
- LangChain with TinyFish
- LangChain with Context.dev
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

TinyFish cases require `TINYFISH_API_KEY` in the environment. Context.dev cases require `CONTEXT_DEV_API_KEY`. Keep provider keys in local env files or shell session variables; do not commit them.

Optional override:

```bash
./.venv/bin/python scripts/brand_intelligence_benchmark.py --cases-file examples/benchmarks/brand_intelligence_acquisition/cases.json
```

Run only configured providers:

```bash
./.venv/bin/python scripts/brand_intelligence_benchmark.py --providers firecrawl,playwright
```
