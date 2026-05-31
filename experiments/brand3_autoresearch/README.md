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

Provisional lab decision:
- prefer the more complete variant by default
- only reject it when it introduces a clear regression in a critical block
- current benchmark evidence: `b` won `5/5` comparison cases (`base44`, `bokeroon`, `fly-io`, `creatify-ai-es`, `heygen`)

Comparator policy:
- the score now weights `mission`, `value_proposition`, `core_purpose`, and `brand_idea` more heavily than peripheral blocks
- a strong regression in a critical block can now outweigh a small global average win

Candidate file convention:
- `candidate/<case_id>.json`
- each file should contain the raw candidate payload for that case, or a `{"payload": ...}` wrapper

Real scan export:
- `python experiments/brand3_autoresearch/export_candidate.py --scan-id <id> --output candidate/<case_id>.json`
- `python experiments/brand3_autoresearch/export_candidate.py --scan-file path/to/scan.json --output candidate/<case_id>.json`

Variant materialization:
- `python experiments/brand3_autoresearch/materialize_variants.py --source-dir candidate --output-a candidate_a --output-b candidate_b`
- `python experiments/brand3_autoresearch/materialize_variants.py --source-file candidate/base44.json --slug base44 --overlay-dir-a overlays/a --overlay-dir-b overlays/b --output-a candidate_a --output-b candidate_b`

Batch history:
- `python experiments/brand3_autoresearch/run_batch.py --spec-file batch/spec.json`
- writes `history/batch_history.jsonl`, `history/batch_summary.json`, and `history/batch_summary.md`
- only emits a recommendation once the batch has enough compare runs
- the default spec lives at `experiments/brand3_autoresearch/batch/spec.json`

Benchmark loop:
- `python experiments/brand3_autoresearch/run_benchmark.py`
- `python experiments/brand3_autoresearch/run_benchmark.py --scan-id <id> --candidate-dir candidate`
- `python experiments/brand3_autoresearch/run_benchmark.py --scan-file path/to/scan.json --candidate-dir candidate`
- `python experiments/brand3_autoresearch/run_benchmark.py --candidate-file path/to/candidate.json --candidate-slug base44`
- `python experiments/brand3_autoresearch/run_benchmark.py --candidate-file candidate_a.json --candidate-file-b candidate_b.json --candidate-slug base44`
- `python experiments/brand3_autoresearch/run_benchmark.py --candidate-dir candidate_a --candidate-dir-b candidate_b`
- writes `runs/report.json` and `runs/report.md`
- prints a `retain` or `revert` decision for the current Analyst Pass benchmark
- with `--candidate-file-b`, prints a `winner` and both candidate scores
- with `--candidate-dir-b`, compares two full candidate directories and prints the winner
