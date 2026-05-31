# Brand3 AutoResearch Harness

Experimental loop for prompt and evaluator work.

Scope:
- candidate prompt files only
- evaluator and scorecard only
- no production routes, storage migrations, or model config changes

Workflow:
1. Edit files under `candidate/` only.
2. Run `python experiments/brand3_autoresearch/eval.py`.
3. Compare the report against the baseline scorecard.
4. Keep the change only if the overall score improves and no hard regression appears.

Candidate file convention:
- `candidate/<case_id>.json`
- each file should contain the raw candidate payload for that case, or a `{"payload": ...}` wrapper

Real scan export:
- `python experiments/brand3_autoresearch/export_candidate.py --scan-id <id> --output candidate/<case_id>.json`
- `python experiments/brand3_autoresearch/export_candidate.py --scan-file path/to/scan.json --output candidate/<case_id>.json`

Benchmark loop:
- `python experiments/brand3_autoresearch/run_benchmark.py`
- `python experiments/brand3_autoresearch/run_benchmark.py --scan-id <id> --candidate-dir candidate`
- `python experiments/brand3_autoresearch/run_benchmark.py --scan-file path/to/scan.json --candidate-dir candidate`
- writes `runs/report.json` and `runs/report.md`
- prints a `retain` or `revert` decision for the current Analyst Pass benchmark
