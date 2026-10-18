# P1-v0 Final Empirical Interpretation

Benchmark: P1_TRACK_A_PRIMEKG_V0

Primary task: disease-cold-start indication ranking

Primary metric: Recall@50

## Canonical portfolio

- E1: 0.043881
- E2: 0.629211
- E3 expected: 0.304901
- E4 expected: 0.269664
- SBS: E2 = 0.629211
- VBS: 0.681351
- SBS-VBS gap: 0.052141

## H1 — Conditional complementarity

Status: SUPPORTED

The canonical four-expert portfolio retains a positive
disease-level oracle opportunity above the single best solver.

## H2 — Stability

Status: SUPPORTED_WITH_MATERIAL_PROTOCOL_SENSITIVITY

The existence of disease-dependent complementarity persists
across seeds, ranking metrics, candidate-universe perturbations,
and therapeutic-label masking protocols.

This does not imply exact winner invariance.

Under strict 2-hop masking:

- VBS disease-level Spearman vs canonical:
  0.635113
- strict unique-winner agreement:
  0.633891
- winner/tie label agreement:
  0.532520

Therefore benchmark protocol materially changes the magnitude
and exact disease-level geometry of expert specialization even
though the portfolio-level complementarity phenomenon persists.

## Static observability

Status: NOT_SUPPORTED_FOR_TESTED_LOW_COST_STATIC_FEATURES

The stable SBS–VBS opportunity was not recoverable by the preregistered family of low-cost static graph descriptors and tested selector policies.

## Primary P1-v0 result

Under the frozen leakage-resistant disease-cold-start benchmark, heterogeneous repurposing experts exhibit persistent disease-dependent complementarity. E2 is the single best solver, but the four-expert virtual best solver retains additional utility across seeds, ranking metrics, candidate-universe perturbations, and therapeutic-label masking protocols. The exact magnitude and disease-level identity of specialization are materially protocol-sensitive.

## Claims not supported by P1-v0

- Exact disease-level winner invariance across protocols.
- Improved utility from the tested static routers.
- Temporal/prospective generalization.
- Therapeutic efficacy.
- Dynamic value-of-computation or costed probing.
