# Phase 2 Gate 3 — evaluator v1.1_tiesafe

The clean evaluator consumes an explicit `ExpertScoreResult`: expert ID/version, disease ID, the exact canonical candidate ID axis, scores, applicability, optional abstention reason, optional seed, and provenance. It imports no expert implementation. The frozen candidate/disease axes, roles, Cell-16 evaluator configuration, and Cell-12 metric policy are accepted only after the Gate-1 registry/hash boundary passes. A score archive with the correct shape but shuffled drug or disease IDs fails before any metric calculation.

Run the registered-score reproduction from the existing CLI:

```text
primekg-repurpose reproduce-evaluator --data-root <root-with-external-score-archives> --json-report outputs/gate3_evaluator_equivalence.json
```

The command also accepts repeated `--score-archive ARTIFACT_ID=PATH` for separately located registered NPZs. It reports missing archives as `REGISTERED_EXTERNAL_NOT_LOCAL` and cannot return `PASS` with no genuine archive. Install `.[evaluator]` for NumPy; no GPU or expert model package is needed.

## Exact Cell-16 semantics

Candidates with `AMBIGUOUS_INDICATION`, `OFFLABEL_ONLY`, or `CONFLICTING_NONINDICATION` roles are **removed before ranking**. `CLEAN_INDICATION` supplies primary positives. `CONTRAINDICATION_ONLY` remains rankable and contributes only to separate safety counts. Unobserved candidates remain unlabeled; they are not asserted to be biological negatives. Scores are cast to float32, as in Cell 16; exact equality of the resulting float32 values defines each tie. No threshold, candidate-ID tie breaker, zero-score removal, or negative-score removal is used.

For a tie block of size `m` beginning after `offset` higher-scored candidates, containing `p` CLEAN positives and contributing `t` of its positions to top K:

- Expected positives contributed: `t·p/m`; Recall@K divides total expected positives by the number of CLEAN positives.
- If no positive is in a higher block, Hit@K is `1 - C(m-p,t)/C(m,t)` at the cutoff block; otherwise it is 1. This is probability of at least one hit, not a threshold on expected hit count.
- For the *first positive-containing block*, `P(first position=j) = C(m-j,p-1)/C(m,p)`. Expected first-hit rank is `offset + (m+1)/(p+1)`. MRR is the sum of `P(first position=j)/(offset+j)` over valid positions, using Cell 16's stable recurrence.
- Contra@K uses `t·c/m` for `c` contraindications in the block. ContraRate@K divides expected count by K. First contraindication rank uses the same first-position expectation with `c`.

K values 10, 50, and 100 are loaded from the frozen config. `Recall@50` is primary utility. An explicitly inapplicable expert gets zero MRR, Recall, Hit, Contra and ContraRate; first-hit and first-contra ranks are NaN. An applicable all-zero vector is **not** an abstention and is evaluated as one full tie. The frozen primary cohort has at least three CLEAN positives per disease; an applicable synthetic disease with no CLEAN positive fails. Cell 16 does not define NaN score ordering, so the clean evaluator rejects NaNs loudly rather than inventing one. Positive/negative infinity remain ordered scores. For small test fixtures with K larger than the candidate count, the top-K count saturates at the candidate count while ContraRate retains K as denominator; the frozen 7,957-drug case never needs that extension.

## Reference equivalence and limits

Six raw score NPZs were retrieved via their exact registry Drive IDs: E3 seeds 0/1/2 and E4 seeds 0/1/2. Their sizes match registry records and their axes match the frozen disease/candidate axes. The registry does **not** contain historical SHA-256 values for these external score archives; the report records observed SHA-256 values and labels hash status `UNKNOWN_HASH` rather than manufacturing verification. Each frozen expert matrix is hash-verified before use.

The archives contain only scores and axes. No separate upstream applicability/status artifact is available, so `status` and `applicable` from each frozen matrix are admitted **only as expert metadata**, as allowed by the Gate-3 contract. Metric columns are never inputs to calculation; they are comparison targets. This means score-to-metric equivalence is independently proven, while the expert-specific source of abstention is not reconstructed in this gate.

| Score archive | Disease rows | Maximum absolute disease-metric difference | Recomputed = frozen macro Recall@50 |
|---|---:|---:|---:|
| E3 seed 0 | 738 | 0 | 0.2918345167963524 |
| E3 seed 1 | 738 | 0 | 0.30365612615190174 |
| E3 seed 2 | 738 | 0 | 0.31921361850047364 |
| E4 seed 0 | 738 | 0 | 0.26732620252612416 |
| E4 seed 1 | 738 | 0 | 0.27047611523025084 |
| E4 seed 2 | 738 | 0 | 0.2711909420806408 |

The comparator uses an explicit `1e-12` strict ceiling to accommodate possible binary-to-text float representation, but **the observed difference is exactly zero** for every configured metric in every row, including primary utility and safety metrics. E1 and E2 NPZs have no registry Drive locator and were not found by exact-name connected Drive search. They remain `REGISTERED_EXTERNAL_NOT_LOCAL`; no E1/E2 metric column was treated as a score. Future retrieval can test them with the same evaluator without implementing their expert algorithms.

Tiny tie-block fixtures exhaustively enumerate all tie-consistent permutations and compare exact permutation averages with analytic Recall, Hit, MRR, first-hit rank, and safety counts. This is independent of Cell 16's code and of expert matrices. No training/scoring expert, SBS/VBS, routing, or Gate-4 implementation was added.
