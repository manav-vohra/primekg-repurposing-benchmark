# Phase 2 Gate 3 handoff — tie-safe evaluator and exact reference equivalence

**Decision: PASS.** Clean evaluator `1.1_tiesafe` recomputed 738 disease rows from each of six genuine registry-indexed raw E3/E4 score archives. Every configured disease-level metric and every corresponding macro Recall@50 matched its hash-verified frozen expert matrix with **maximum absolute difference 0**. No expert scoring/training logic, SBS/VBS, routing, or Gate-4 work was implemented. Frozen benchmark/reference files and historical source remain unchanged.

## Changed files and clean API

- `src/primekg_repurposing/evaluation.py` — `ExpertScoreResult`, `TieSafeEvaluator`, Cell-16 analytic tie formulas, hash-bound frozen loader, score-archive comparator, and CLI formula checks.
- `src/primekg_repurposing/cli.py` — `reproduce-evaluator` command with registered score-path overrides and JSON output.
- `tests/test_evaluation.py` — 30 focused tests, including exhaustive tie-block permutation comparisons and opt-in real-score integration.
- `pyproject.toml` — evaluator dependency extra and updated package description.
- `.github/workflows/gate1-validation.yml` — workflow naming; the ordinary CPU test suite includes synthetic evaluator tests.
- `docs/gate3_tiesafe_evaluator.md` and `docs/migration/migration_plan.md` — semantics and gate status.
- `outputs/gate3_evaluator_equivalence.json` and this handoff — machine-readable and human-readable results.

The minimal future-expert result contract holds expert ID/version, disease ID, **ordered** candidate IDs, score vector, explicit applicability and abstention reason, optional seed, and provenance. The evaluator validates benchmark/evaluator identity, disease identity, canonical candidate-axis identity and uniqueness, shape, and frozen roles/configuration through Gate 1. It imports no E1/E2/E3/E4 algorithm.

## Metric, role, and abstention semantics

Ignored roles (`AMBIGUOUS_INDICATION`, `OFFLABEL_ONLY`, `CONFLICTING_NONINDICATION`) are removed **before** metric ranking. `CLEAN_INDICATION` is positive. `CONTRAINDICATION_ONLY` remains rankable and contributes to explicit safety metrics. Unobserved pairs remain unlabeled, not true negatives. Scores are evaluated as float32 with exact-score tie blocks. NaNs are rejected because Cell 16 provides no NaN ordering; infinities remain ordered. No score threshold, candidate-ID tie breaker, zero-score removal, or negative-score removal is used.

For a tie of size `m` with `p` CLEAN positives and `t` top-K slots, expected positive count is `t·p/m`; Recall@K divides by total CLEAN positives. Hit@K is the exact hypergeometric probability of at least one positive in the cutoff tie, unless an earlier tie already contains a positive. For the first positive-containing tie, `P(minimum position=j)=C(m-j,p-1)/C(m,p)`; expected first-hit rank is `offset+(m+1)/(p+1)`, and MRR sums this probability divided by `offset+j`. Contra@K analogously uses `t·c/m`, ContraRate@K divides by K, and first-contra rank uses the same first-position formula. K values 10/50/100 come from the frozen config; Recall@50 is primary utility.

An explicit abstention gets zero Recall, Hit, MRR, Contra and ContraRate, with NaN first-event ranks. Applicability is **not** inferred from scores: an applicable all-zero vector is evaluated as one full tie. The six NPZs contain scores and axes, but no independent expert-status array. The frozen matrices therefore supply `status` and `applicable` only as permitted expert metadata; metric columns remain comparison targets, never inputs. This limitation means expert-specific abstention causation is not reconstructed here.

## Genuine score-to-matrix equivalence

The six NPZ files were fetched from the registry's exact connected-Drive IDs. Their sizes and candidate/disease axes match registry/frozen contracts. Historical SHA-256 values were **not** supplied for these score archives, so the report honestly labels their registry hash status `UNKNOWN_HASH` and records newly observed digests; it does not claim historical hash verification. Every reference matrix was hash-verified against Gate 1 before comparison. The strict comparison ceiling is `1e-12`, but all observed differences—including MRR, first-hit, contraindication metrics, and primary utility—are exactly zero.

| Raw score archive | Rows | Max disease-metric difference | Recomputed = frozen macro Recall@50 |
|---|---:|---:|---:|
| E3 seed 0 | 738 | 0 | 0.2918345167963524 |
| E3 seed 1 | 738 | 0 | 0.30365612615190174 |
| E3 seed 2 | 738 | 0 | 0.31921361850047364 |
| E4 seed 0 | 738 | 0 | 0.26732620252612416 |
| E4 seed 1 | 738 | 0 | 0.27047611523025084 |
| E4 seed 2 | 738 | 0 | 0.2711909420806408 |

Each archive has 736 `OK` diseases and two explicit `ABSTAIN_NO_NONTHERAPEUTIC_KG_CONTEXT` diseases, according to its matrix metadata. E1 and E2 score NPZs remain `REGISTERED_EXTERNAL_NOT_LOCAL`: the registry provides no Drive IDs for them, and exact-name connected-Drive search returned none. Their frozen metric columns were **not** used as surrogate scores. The evaluator can test them later if their original archives are supplied.

## Independent verification and unresolved ambiguities

Small-fixture tests cover no ties, above/below/crossing-cutoff ties, single/multiple positives, earlier plus later positives, all-tied and all-zero applicable scores, ignore-role filtering, contraindications, unknown pairs, explicit abstention, axis/identity corruption, malformed and NaN vectors, infinities, empty CLEAN truth, and K beyond a tiny fixture's length. Brute force enumerates all tie-consistent permutations for each tiny case and agrees with analytic Recall, Hit, MRR, first-hit and safety metrics. The command's own 19 formula checks include 48 independently enumerated permutations.

The full local suite, with exact raw PrimeKG and real E3 seed-0 score archive enabled, passes **85 tests with zero skips or failures**. Gate-1 reference validation still verifies all 50 bundled frozen files with zero failures; its overall `PARTIAL` state is solely for unrelated nonlocal registered artifacts. The remaining uncertainties are the original E1/E2 NPZ locations, absent historical score hashes for E3/E4, and separate upstream provenance for expert applicability. None is hidden by the score-to-metric equivalence claim.

**Proposed next gate:** `PHASE 2 GATE 4 — E1 WEIGHTED GENE-SIMILARITY EXPERT + EXACT SCORE/METRIC REPRODUCTION`. Gate 4 has not begun.
