# Context.dev Capability Benchmark

This lab benchmark probes Context.dev endpoints as candidate acquisition
surfaces for Brand3. It is not wired into production.

Default capabilities:

- `retrieve_brand`
- `styleguide`
- `fonts`
- `images`
- `screenshot`
- `products`

Run:

```bash
CONTEXT_DEV_API_KEY=... ./.venv/bin/python scripts/contextdev_capability_benchmark.py
```

Run a cheaper subset:

```bash
CONTEXT_DEV_API_KEY=... ./.venv/bin/python scripts/contextdev_capability_benchmark.py --capabilities retrieve_brand,styleguide,fonts
```

Keep API keys in local environment variables. Do not commit them.
