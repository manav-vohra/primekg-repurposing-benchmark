# Benchmark reconstruction gap analysis

> **Superseded conclusion (2026-10-05):** The Phase-1 conclusion below accurately described the first ingest bundle but is no longer the active provenance assessment.

## Conclusion

True from-scratch benchmark reconstruction is **not currently possible** from this bundle. The benchmark can be consumed and hash-checked, and E1–E4 can in principle be rerun against retrieved frozen inputs, but the logic that creates the benchmark foundation and E3 encoded corpora is absent.

| Artifact group | Classification | Basis |
|---|---|---|
| `kg.csv` | FROZEN_ARTIFACT_ONLY | External Drive ID, size, and SHA survive; acquisition/snapshot code absent |
| Therapeutic role table | FROZEN_ARTIFACT_ONLY | Table survives; classification logic absent |
| Candidates, diseases, truth, eval roles | FROZEN_ARTIFACT_ONLY | Tables survive; producers absent |
| K8 quarantine and fold summary | FROZEN_ARTIFACT_ONLY | Tables survive; split/stratification/buffer code absent |
| Tie-safe evaluator config | FROZEN_ARTIFACT_ONLY | Config survives; producing step absent; evaluator code is duplicated in expert sources |
| E3 entity/relation tables | FROZEN_ARTIFACT_ONLY | Tables survive; Cell 19/19B absent |
| E3 base/CLEAN NPZ corpora | FROZEN_ARTIFACT_ONLY | External IDs and hashes survive; binaries and producer absent locally |
| E3 fold-label manifest | MISSING | Only SHA survives |
| Metric policy | MISSING | Only path, size, and SHA survive |
| E1/E2 results | AUTHORITATIVELY_REBUILDABLE | Authoritative source and reference matrices survive; requires verified external `kg.csv` |
| E3/E4 results | AUTHORITATIVELY_REBUILDABLE | Authoritative source and matrices survive; requires verified external corpora and locked runtime |
| Canonical E4 reimplementation | REBUILDABLE_WITH_RECOVERED_LOGIC | Utility-level fidelity audit passed, but its actual source is absent and it is not the historical canonical result |
| Routing/actionability | UNCERTAIN | Only references/claims survive in this bundle |

The machine-readable classification is in `artifacts/manifests/benchmark_reconstruction_gap_analysis.json`.

## Required recovery before a from-scratch claim

Recover and hash: benchmark-construction cells/scripts; the metric-policy file; Cell 19/19B; the fold-label manifest; raw-graph acquisition/version metadata; and the exact environment/seed/backend record. Then regenerate each benchmark artifact into a temporary directory and require byte equality or a documented semantic-equivalence contract.

## Phase-2 revised conclusion

The complete historical producer chain from the hash-identified raw `kg.csv` through the frozen P1-v0 benchmark now exists in recovered Cells 1/1B-1E and 2-13. Cell 16 closes the evaluator-source gap. Cells 19, 19A and 19B close the E3-corpus lineage gap while preserving the original defect, forensic localization, and correction. The metric policy and fold-label manifest are recovered frozen contracts.

| Stage | Revised state |
|---|---|
| `kg.csv` | EXTERNAL_INPUT_SURVIVES; historical acquisition/validation source recovered; exact SHA-256 required |
| census/canonical therapeutic pairs | HISTORICAL_SOURCE_RECOVERED; exact comparison possible |
| roles/CLEAN/candidates/cohort/truth/eval roles | HISTORICAL_SOURCE_RECOVERED + FROZEN_OUTPUT_SURVIVES + EXACT_RECONSTRUCTION_TEST_POSSIBLE |
| K8 folds/quarantine/benchmark freeze | HISTORICAL_SOURCE_RECOVERED + FROZEN_OUTPUT_SURVIVES + EXACT_RECONSTRUCTION_TEST_POSSIBLE |
| evaluator/metric policy | HISTORICAL_SOURCE_RECOVERED + RECOVERED_FROZEN_CONTRACT |
| E3 corpus | Cell 19 defective; 19A forensic; 19B corrective and authoritative for final corpus; large binaries external |

Therefore raw PrimeKG to frozen P1-v0 reconstruction is now possible from historical source once the exact external `kg.csv` is retrieved and verified. No stage was rerun in this reconciliation, and a clean reimplementation plus golden equivalence tests is still required.
