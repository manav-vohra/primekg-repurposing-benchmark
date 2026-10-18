# Reproducibility tiers

| Tier | Inputs | Compute | Outputs | Verification gate |
|---|---|---|---|---|
| SMOKE | Tiny synthetic graph, roles, folds, and scores committed under `tests/fixtures/` | CPU, seconds, no network | Test-only E1–E4 forward outputs, metrics, masks | All unit tests; hand-computable tie cases; prohibited labels absent; deterministic rerun equality |
| ANALYSIS_ONLY | Frozen eight expert matrices plus final expected-oracle/reference metadata | CPU, low memory, under minutes | Per-disease expected utilities, SBS/VBS, winner/tie counts, bootstrap tables/figures | Exact E1/E2/E3/E4 macro values within declared tolerance; SBS/VBS/gap and winner counts match frozen sentinels; no score averaging |
| DETERMINISTIC | Verified `kg.csv`; frozen benchmark/role/quarantine/evaluator artifacts | CPU with enough RAM for chunked 982 MB CSV; likely minutes to hours | E1/E2 score tensors, matrices, metadata, preliminary oracle | Input hashes pass; candidate/disease axes exact; E1/E2 status vectors and every metric column match frozen matrices within a predefined numeric/serialization tolerance |
| FULL | All DETERMINISTIC inputs plus verified E3 base/CLEAN corpora, entity/relation tables, locked GPU runtime | CUDA GPU, substantial memory; 8 folds × 3 seeds for each of E3/E4 | Checkpoints, scores, logs, matrices, expected utilities, four-expert oracle, provenance records | Masking/leakage gates pass per fold; seeds/config/backend recorded; each seed matrix compared to historical reference; expected-utility/oracle sentinels pass; historical vs fresh labels remain distinct |

FULL is not a from-scratch benchmark build: it retrains experts against frozen benchmark artifacts. A separate future `REBUILD_BENCHMARK` operation should exist only after missing producer logic is recovered and validated.

## Phase-2 revision

`REBUILD_BENCHMARK` is now provenance-enabled: the historical source chain and frozen targets survive. Its inputs are the exact hash-verified `kg.csv` plus recovered Cells 2-13; its output gate is exact artifact identity where serialization permits, otherwise an approved schema/order/value equivalence contract. This tier has not yet been executed.

E1/E2 are source-, input-, and output-reproducible deterministic computations; bytewise serialized equality remains unproven. E3/E4 are source-, input-, training-, and output-reproducible after external objects are retrieved; scientifically equivalent reruns are expected, but bitwise GPU reproduction is not promised. `ANALYSIS_ONLY` can reproduce headline SBS/VBS/oracle results and recovered routing/actionability closures without retraining.
