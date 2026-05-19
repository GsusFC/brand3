# Brand3 Linear Prompt Input Generation Trial Review

Date: 2026-05-18  
Case: Linear  
Dimension: `diferenciacion`  
Scope: controlled non-runtime generation. No report mutation, no prompt rollout, no scoring/rendering changes.

## Goal

Compare the current Brand3 findings input against the Evidence Packet prompt-input candidate using the same model and the same output shape.

## Result

| Input | evidence count | findings | titles | risky terms detected |
| --- | ---: | ---: | --- | --- |
| Current Brand3 input | 5 | 2 | Self-Description as Agent Collaborative System, Contrast Between Product Pitch and Content Tone | strategy, strategic |
| Evidence Packet candidate | 2 | 1 | Relative Positioning Distance Among Measured Competitors | strategy |

## Reading

The candidate input is materially cleaner. It reduces the differentiation input from five mixed evidence items to two bounded competitor-comparison items. The generated candidate output stays closer to the actual evidence and produces one finding: relative positioning distance among measured competitors.

The current input generated two broader findings: one around agent collaboration and another around contrast between product pitch and content tone. Both may be plausible, but they are less tightly tied to the comparison evidence and move faster into strategic interpretation.

## Critical Limit

This was not a full success.

The shared findings schema still requires `typical_decision`. That field pulls even the candidate output back toward strategic option framing. The candidate output is much cleaner than the current output, but it still includes strategy language because the production findings contract asks for it.

So the bottleneck has moved:

- Evidence Packet improves the input contract.
- The existing findings prompt/schema still pushes the model toward strategic prose.

## Decision

Evidence Packet prompt input is better than current input, but not ready for runtime integration.

Next step should be narrow: design a lab-only findings prompt/schema for Evidence Packet inputs that removes `typical_decision` or replaces it with a limits/abstention field. Then rerun only Linear `diferenciacion`.

## Artifacts

- `examples/reports/evidence_packet_prompt_input_generation/linear/current_prompt.json`
- `examples/reports/evidence_packet_prompt_input_generation/linear/candidate_prompt.json`
- `examples/reports/evidence_packet_prompt_input_generation/linear/current_output.json`
- `examples/reports/evidence_packet_prompt_input_generation/linear/candidate_output.json`
- `examples/reports/evidence_packet_prompt_input_generation/linear/comparison.json`
- `examples/reports/evidence_packet_prompt_input_generation/linear/cost_observation.json`
