# Gated migration plan

Each gate stops on failure. Historical sources remain immutable.

## Gate 0 — Recover the missing foundation

**Reconciliation status: SATISFIED as provenance recovery.** The items requested below were recovered. Large external objects still require retrieval/hash verification at the first implementation gate.

- Files changed: `provenance/` manifests only; no `src/` scientific code.
- Behavior: none; collect benchmark producer source, Cell 19/19B, metric policy, fold-label manifest, raw-data licensing/version record, and exact environment metadata.
- Test: hashes match surviving references; source-to-output references are explicit.
- Reference: benchmark/corpus manifests and hashes in this audit.
- Proceed when: every benchmark-foundation edge has an identified producer or is formally declared frozen-input-only.

## Gate 1 — Artifact and benchmark foundation

**Gate-1 implementation status (2026-10-05): complete.** The registry, SHA-256/schema/axis/identity validator, external registration, three validation tiers, CLI, JSON report, focused corruption tests, and CPU-only CI are in place. The REFERENCE run verifies 50 supplied small files and reports external/archive entries as partial. See `docs/gate1_artifact_validation.md`.

Actual implementation: `src/primekg_repurposing/provenance.py`, `src/primekg_repurposing/cli.py`, `artifacts/registry.json`, `artifacts/frozen/`, and `tests/test_provenance.py`. The earlier proposed file layout below is retained as a Phase-1 planning record.

- Phase-1 proposed files: `src/primekg_repurpose/data/{artifacts,ordering,primekg,corpus}.py`, `benchmark/{contract,validation}.py`, configs, tests.
- Behavior: load and validate frozen artifacts without rebuilding them.
- Test: exact hashes, schemas, counts, unique IDs, candidate/disease/entity/relation arrays.
- Reference: bundled benchmark files; external hashes for `kg.csv` and corpora.
- Proceed when: all identity/order gates pass and no path is machine-specific.

## Gate 2 — Masking

**Gate 2A status (2026-10-05): complete for frozen semantics.** The clean benchmark view, CANONICAL_1HOP mask, all eight legal CLEAN counts, target/buffer exclusion, scoped direct ontology exposure audit, long-ID regression, and structural-preservation contract are implemented and tested. See `docs/gate2a_frozen_fold_semantics.md`. Individual target–neighbor edges remain unenumerated until the exact raw graph is available.

**Gate 2B status (2026-10-05): PASS.** The exact registry-hash-verified raw `kg.csv` was available locally. The clean producer independently reconstructs the cohort, fold assignment, direct ontology quarantine, and all seven requested benchmark artifacts. Six benchmark CSVs are byte-identical to frozen references. The benchmark manifest has identical scientific content and hashes to the historical bytes when only the recorded Python/pandas/NumPy versions are normalized. The Cell-12 metric-policy prerequisite is byte-identical. See `docs/gate2b_raw_reconstruction.md` and `outputs/gate2b_reconstruction.json`.

**Next task only:** Phase 2 Gate 3 — tie-safe evaluator reconstruction and exact reference equivalence. No evaluator or scientific expert is implemented by Gate 2B.

- Gate 2A behavior: consume frozen quarantine and compute legal supervision masks.
- Gate 2B behavior: produce independent benchmark artifacts from exact raw PrimeKG into a separate generated directory; compare science, ordering, and hashes against frozen references.
- Reference: Gate-1 registry, historical Cells 2–13, frozen benchmark files and graph census.

## Gate 3 — Evaluator v1.1_tiesafe

**Gate 3 status (2026-10-06): PASS for six genuine E3/E4 score archives.** The evaluator recomputes all configured disease-level primary and contraindication metrics from registry-indexed raw scores. Every compared metric has maximum absolute difference zero against its hash-verified frozen expert matrix; all six macro Recall@50 values match exactly. E1/E2 score archives remain registered external-not-local and were not reconstructed from expert algorithms or metric columns. See `docs/gate3_tiesafe_evaluator.md` and `outputs/gate3_evaluator_equivalence.json`.

- Files changed: `evaluation/{tiesafe,metrics,applicability}.py`, unit/golden tests.
- Behavior: ignored roles, exact ties, Recall/Hit/MRR/first-hit, safety metrics, explicit abstention.
- Test: exhaustive synthetic tie cases plus re-evaluate frozen score tensors when recovered; disease 40797 seed-0 E3 remains abstained.
- Reference: evaluator config and frozen expert matrices.
- Proceed when: every metric/status column matches golden expectations.

## Gate 4 — E1

- Files changed: `experts/e1_weighted_gene.py`, E1 config/tests/script.
- Behavior: Cell 14 weighted cosine and abstention.
- Test: gene weights and synthetic scores; exact applicable/status vector; full disease metrics equal frozen E1 matrix within predefined tolerance.
- Reference: `p1_e1_expert_matrix_v1_1_tiesafe.csv` and recovered score NPZ when obtained.
- Proceed when: deterministic reruns match.

## Gate 5 — E2

- Files changed: `experts/e2_label_transfer.py`, E2 config/tests.
- Behavior: Cell 17 binary TF-IDF, cosine, all-legal-neighbor label transfer, no KNN.
- Test: no therapeutic feature tokens; legal-label mask; exact status vector; matrix equality.
- Reference: frozen E2 matrix and recovered score NPZ when obtained.
- Proceed when: canonical matrix and U0 evaluator reproduce.

## Gate 6 — E3

- Files changed: `experts/e3_complex.py`, E3 config/tests.
- Behavior: Cells 20/21 two-stage training and seeds 0/1/2.
- Test: Stage A has zero therapeutic edges; same-type corruptions; Stage B drug-head corruptions; fixed schedules; per-seed matrix comparison; disease-level mean recomputation.
- Reference: three E3 matrices and historical expected metrics.
- Proceed when: all fold masking tests and declared numeric fidelity thresholds pass without tuning.

## Gate 7 — E4

- Files changed: `experts/e4_rgcn.py`, E4 config/tests.
- Behavior: Cells 24/25 architecture/training plus Cell 43 conventions.
- Test: two-layer 64/4/27 architecture, mean aggregation, right transform, ReLU/none, `drug @ M @ disease`, fold supervision, per-seed matrix comparison.
- Reference: three E4 matrices, Cell-43 forward audit, canonical-reimplementation fidelity audit.
- Proceed when: label output as historical reproduction only if the historical gate passes; otherwise label fresh reimplementation and preserve the delta.

## Gate 8 — Aggregate analysis

- Files changed: `analysis/{expected_utility,oracle}.py`, analysis script/tests.
- Behavior: disease-level seed means, SBS/VBS, ties, bootstrap.
- Test: SBS `0.6292107026825583`; VBS `0.681351211065284`; gap `0.05214050838272566`; winner counts 39/442/38/56/163; two no-applicable diseases fixed to zero.
- Reference: expected-oracle CSV and uncertainty JSON.
- Proceed when: no lucky-seed or raw-score average path exists.

## Gate 9 — Robustness

- Files changed: `analysis/robustness.py`, recovered-provenance mapping, tests.
- Behavior: candidate universes and TARGET_ONLY/CANONICAL_1HOP/STRICT_2HOP.
- Test: canonical U0/1-hop exactly reproduces frozen utility/status before variants run.
- Reference: recovered Cells 36/38/40 and recovered missing outputs.
- Proceed when: all preregistrations/results are recovered and lineage is complete.

## Gate 10 — Routing/actionability

- Files changed: `analysis/routing.py` only after source recovery.
- Behavior: legal pre-label/static features and costed probes.
- Test: feature manifests exclude therapeutic/outcome data; sealed META_TEST remains unopened; costs charged pre-target.
- Reference: missing feature/probe/closure artifacts named in leakage audit.
- Proceed when: sources and referenced hashes are recovered; otherwise omit this executable layer and document historical claims only.

## Gate 11 — Documentation and release

- Files changed: README, data/license cards, reproduction guide, CI/container/lock files, curated artifact index.
- Behavior: none.
- Test: clean clone runs SMOKE and ANALYSIS_ONLY; optional downloads hash-check; secret/license scans pass; provenance is never imported by `src/`.
- Reference: all prior gates.
- Proceed when: independent reviewer can distinguish historical, recovered, clean, generated, and reference artifacts.

## Exact recommended Phase 2 task

Build only an artifact/provenance loader and validator. It must distinguish `CURRENT_RECOVERED_NOTEBOOK`, `RECONSTRUCTED_PRE_RECOVERY_SNAPSHOT`, and `HISTORICAL_SOURCE_CELLS`; locate or retrieve the exact `kg.csv`; verify every available SHA-256, schema, axis, count, and manifest; represent indexed Drive objects as `FOUND_EXTERNAL_NOT_BUNDLED`; and emit a closed validation report. Do not implement a scientific transformation until this gate passes.
