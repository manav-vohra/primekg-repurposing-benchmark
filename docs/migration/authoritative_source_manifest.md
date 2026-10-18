# Authoritative source manifest

> **Phase-2 reconciliation (2026-10-05):** The Phase-1 finding below is retained as history. The active source baseline now also includes the recovered historical notebook producer cells. See `phase1_reconciliation.md`.

## Finding

Seven bundled files are explicitly authoritative historical sources: E1 Cell 14, E2 Cell 17, E3 Cells 20 and 21, E4 training Cells 24 and 25, and E4 forward-recovery Cell 43. Their hashes match the bundle manifest and the supplied known-hash verification where covered. Six recovered files are byte-identical duplicates of those sources. The remaining recovered files are evidence-bearing candidates, failed/superseded attempts, or later robustness/forensic analyses; none is promoted to authoritative merely from its filename.

The machine-readable record is `artifacts/manifests/authoritative_source_manifest.json`.

## Named authoritative sources

| File | Cell | SHA-256 | Scientific role | Key unresolved issue |
|---|---:|---|---|---|
| `E1_authoritative.py` | 14 | `b4dc0191…f1f0900` | Weighted gene cosine and evaluation | Tie-safe matrix regeneration step is not separately preserved |
| `E2_authoritative.py` | 17 | `96607e0e…c01fe2f` | TF-IDF disease similarity and legal-label transfer | Benchmark/role/quarantine producers absent |
| `E3_authoritative.py` | 20 | `14712fef…c1648c` | ComplEx seed 0, two stages | Corpus-producing Cell 19 absent |
| `E3_seed12_support.py` | 21 | `af61b414…56224` | ComplEx seeds 1–2 and disease-utility averaging | Logs/checkpoints/scores absent |
| `E4_training_seed0.py` | 24 | `d6f8b3b3…c11680` | Original R-GCN seed 0 | Feasibility record/checkpoints/scores absent |
| `E4_training_seed12.py` | 25 | `46975170…b3d3f` | Original R-GCN seeds 1–2 and expected utility | Most direct outputs absent |
| `E4_authoritative.py` | 43 | `a476b743…965cc` | Forward-pass semantic recovery | Exact raw-logit gate failed (MAE `2.270696e-4` > `1e-4`) |

## Recovered-source disposition

- Byte-identical duplicates: E1 candidate 0; E2 candidate 0; E3 candidates 0–1; E4 candidates 0–2.
- Useful but non-authoritative analyses: E2 Cell 18, Cell 27, corrected Cell 36, Cell 38; E3 Cell 40; E4 Cells 44, 45, corrected 46, and 47.
- Failed/superseded: initial E2 Cell 36 and initial E4 Cell 46.
- Missing companion/reference source: E2 Cell 36B, benchmark-construction cells, E3 Cell 19, E4 Cell 42, and routing/actionability source files referenced by audit records.

## Interpretation rule

“Authoritative” here means historical source-of-truth evidence, not independently reproduced behavior. No source was executed during this audit.

## Phase-2 recovered historical-source layer

The Drive notebook named `hgt-sde ` is internally `P1_Benchmark_Feasibility.ipynb`. Treat its three representations separately: `CURRENT_RECOVERED_NOTEBOOK` (131 cells, with three appended recovery cells), `RECONSTRUCTED_PRE_RECOVERY_SNAPSHOT` (128 cells, not byte-identical to the recorded Drive revision), and individually hash-verified `HISTORICAL_SOURCE_CELLS`.

Newly authoritative producer evidence includes Cells 1/1B-1E (retrieval/validation), 2-13 (graph census through benchmark freeze), 16 (tie-safe evaluator), 19 (diagnosed defective U128 corpus path), 19A (forensic reconciliation), 19B (corrective corpus freeze), 27-34 (portfolio/static routing), and 56-72 (cost/actionability). Cell 19 is `HISTORICAL_SOURCE_WITH_DIAGNOSED_DEFECT`; Cell 19A is `HISTORICAL_FORENSIC_RECONCILIATION`; Cell 19B is `HISTORICAL_CORRECTIVE_SOURCE`. These classifications are not interchangeable.

The seven previously authoritative exports remain authoritative and now have independent byte-for-byte notebook-cell corroboration. Large E3/E4 objects indexed by Drive ID/size are `FOUND_EXTERNAL_NOT_BUNDLED`, not missing. Machine-readable additions are under `reconciliation_2026_10_05` in the JSON manifest.
