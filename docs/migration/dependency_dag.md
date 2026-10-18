# Artifact dependency DAG

> **Phase-2 reconciliation:** The Phase-1 graph below is retained as the original bundle-only view. Its `MISSING` producers are superseded by the active recovered graph that follows.

The complete machine-readable graph is in `artifacts/manifests/artifact_dependency_dag.json`.

```text
kg.csv [external frozen; producer MISSING]
├─> therapeutic_pair_evaluation_roles.csv [producer MISSING]
│   ├─> primary diseases / truth / primary eval roles [producer MISSING]
│   ├─> quarantine + fold summary [producer MISSING]
│   ├─> E2 legal CLEAN supervision
│   └─> E3 clean-indication corpus [Cell 19/19B MISSING]
├─> candidate drugs [producer MISSING]
├─> quarantine ontology buffers [producer MISSING]
├─> E3 entity/relation vocabularies [Cell 19/19B MISSING]
├─> E3 nontherapeutic triple corpus [Cell 19/19B MISSING]
├─> E1 biological profiles
├─> E2 nontherapeutic disease profiles
└─> routing static features [producer MISSING]

frozen benchmark + evaluator + E3 corpora
├─> E1 matrix
├─> E2 matrix
├─> E3 seed matrices ─> per-disease expected E3 utility
└─> E4 seed matrices ─> per-disease expected E4 utility

E1 + E2 + expected E3 + expected E4
└─> expected oracle table ─> SBS/VBS / robustness ─> routing/actionability
```

## Known exact producers

- E1: authoritative Cell 14.
- E2: authoritative Cell 17.
- E3 seed 0: authoritative Cell 20; seeds 1–2 and expected utility: Cell 21.
- E4 seed 0: authoritative Cell 24; seeds 1–2 and expected utility/oracle: Cell 25.

## Active recovered graph

```text
kg.csv -> Cells 2-3 census/canonical pairs -> Cell 11 roles/CLEAN
       -> Cells 9,11-13 candidates/cohort/truth/eval roles
       -> Cell 12 folds/quarantine -> Cell 13 benchmark freeze
       -> Cell 16 tie-safe evaluator
       -> Cells 14/17 E1/E2
       -> Cell 19 (defective) -> 19A (forensic) -> 19B (corrective E3 corpus)
       -> Cells 20/21 E3 and Cells 24/25 E4
       -> seed matrices -> expected disease utilities -> SBS/VBS/oracle
       -> bootstrap/winners/robustness -> observability/static routing
       -> Gate A -> Gate B/costed probing
```

Every raw-to-benchmark producer edge now has historical source. Exact reconstruction can be tested against frozen artifacts. E3/E4 corpora, checkpoints, and score tensors that remain in Drive are `FOUND_EXTERNAL_NOT_BUNDLED`. The JSON file preserves the original graph and adds an explicit active `phase2_reconciliation` graph.
- Cross-metric portfolio: recovered, non-authoritative Cell 27.
- Candidate-universe robustness: corrected recovered Cell 36; initial Cell 36 failed its U0 gate.
- E2/E3 protocol robustness: recovered Cells 38/40.

## Broken lineage edges

The exact producer is missing for raw graph acquisition, therapeutic role classification, primary-cohort selection, folds, quarantine, evaluator config, E3 vocabulary/corpus construction, E4 feasibility, E4 checkpoint recovery, and all routing/actionability artifacts. Audit files naming those missing products are evidence of existence, not substitutes for producing source.
