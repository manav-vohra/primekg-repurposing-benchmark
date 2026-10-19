# Phase 2 Gate 6A handoff

## Decision

**PASS.** E3 corpus, protocol, architecture, checkpoint compatibility, historical score-archive identity, applicability, and the pre-training Gate-6B execution contract are validated. No Stage-A or Stage-B training was launched. No E4 or downstream portfolio analysis was implemented.

## Corrected corpus contract

- Correct target: Cell 19B (`HISTORICAL_CORRECTIVE_SOURCE`), not Cell 19's diagnosed `U128` defect.
- Raw PrimeKG scan: 8,015,236 nontherapeutic directed rows retained and 85,262 therapeutic rows removed.
- Representation: source direction and row order preserved, duplicates preserved, no inverse relations, no normalization.
- Entity vocabulary: 129,307 lexical composite keys; SHA-256 `4602c6e372d8db30463c5e5dae418632ce742de9255e305809c1d99829ca8fa3`.
- Relation vocabulary: 28 lexical names; SHA-256 `591c5fe76d4122369574972525f6b5e82128d8e975264f6cfdce6178b223caba`.
- Base archive: 8,015,236 triples (`head:int32`, `relation:int16`, `tail:int32`); SHA-256 `4b13562268f237b4217002279338a721e9c6b9c30fa178d29883066848fd733b`.
- CLEAN archive: 9,177 drug-head → `clean_indication` → disease-tail triples with inferred `<U523` disease storage; SHA-256 `06573916aa538640949c4fceb79acb4455856aaf2038cd44df5c54675a30c0b3`.
- Long-ID regression: 25 CLEAN rows exceed 128 characters, maximum length 523; all remain complete and match the intended masks.
- Fold legal CLEAN counts from `FrozenBenchmark.mask`: `6856, 6828, 6990, 7119, 6871, 7183, 7091, 6827`; target/buffer leaks: zero.

## Recovered ComplEx contract

- Four float32 embeddings: sparse entity real/imaginary `(129307, 64)` and dense relation real/imaginary `(28, 64)`.
- Initialization: uniform `[-1/sqrt(64), +1/sqrt(64)]`.
- Score: `sum(hr*rr*tr + hi*rr*ti + hr*ri*ti - hi*ri*tr)`.
- No embedding normalization and no explicit regularization.
- Loss: `mean(softplus(-positive)) + mean(softplus(negative))`.
- Optimizers: entity `SparseAdam`, relation `Adam`, default optimizer parameters except frozen learning rates; relation gradient norm clipped at 5.0, sparse entity gradients not clipped.
- Historical device: CUDA required; Cells 20/21 explicitly required a Colab A100. Historical package, CUDA, driver, and exact GPU versions are unknown.

Stage A: 2 epochs; batch 131,072; one contrast per positive; 50/50 head/tail corruption; replacement from the base-active same-type pool with the original excluded when possible; entity/relation LR 0.01.

Stage B: fresh strict load of the seed's Stage-A state for every fold; 80 epochs; positive batch 2,048; 16 candidate drug-head contrasts per positive; reject all legal CLEAN heads for the same disease; entity LR 0.002, relation LR 0.01; fold RNG `10000 + seed*100 + fold`; no early stopping or validation tuning.

Corrupted samples are optimization contrasts only. They are not contraindications, biological negatives, confirmed non-indications, or benchmark negative ground truth.

## Historical checkpoint validation

All hashes below are `RECOVERY_TIME_OBSERVED`, not historical-time hash verification.

| Seed | Bytes | Observed SHA-256 | Strict load | Independent probe |
|---:|---:|---|---|---|
| 0 | 66,222,433 | `505a9929421c761222411eb83e1e7ce9ee27e84842561ab7a4f05b26f5fd2c88` | PASS | bitwise equal; max abs diff 0.0 |
| 1 | 66,222,433 | `db6d19c0e9a901c9886655e48c4efc9ed50497b5edf79303a84d8c5fe683eb3b` | PASS | bitwise equal; max abs diff 0.0 |
| 2 | 66,222,433 | `d0b0f43969b3fef3f333a185ed64d9d4909d6692f2b0efb0c43b01b218c295a1` | PASS | bitwise equal; max abs diff 0.0 |

No legacy-key adapter or checkpoint rewrite was needed.

## Historical final score targets

All three archives are float32 arrays of shape `(738, 7957)` with exact frozen disease and candidate axes.

| Seed | Bytes | Recovery-time SHA-256 | Exact macro Recall@50 |
|---:|---:|---|---:|
| 0 | 20,977,038 | `c85f1e68436e24d7da51cf5a6a0617abadcc858fea5a01492de9b2c8befc731c` | 0.2918345167963524 |
| 1 | 20,858,395 | `8f9835fbeb7d79c0944705aaaf50414b757d28fa8307a38a4aae9ed5ac774fe7` | 0.30365612615190174 |
| 2 | 20,929,137 | `028c299a3356ef628365bcdb3a00f12e2ceb56a166aa0f01a4c5ca01641b1007` | 0.31921361850047364 |

## Applicability and environment

Historical applicability is `OK` when the target disease has at least one nontherapeutic base-graph edge, followed by finite/nonconstant score checks. Cells 20/21 establish the graph-context rule; the frozen downstream expert matrix confirms 736 `OK` and 2 `ABSTAIN_NO_NONTHERAPEUTIC_KG_CONTEXT` because no separate upstream status archive survives.

Available validation runtime: CPython 3.12.14, NumPy 2.3.5, pandas 3.0.1, SciPy 1.18.1, PyTorch 2.14.1+cpu, Windows 10. This CPU runtime was used only for validation and probes, not canonical training.

## Verification and deliverables

- Full suite: **154 passed, 10 skipped**.
- Gate report: `outputs/gate6a_e3_preparation.json`.
- Raw-scan evidence: `outputs/gate6a_raw_corpus_scan.json`.
- Frozen Gate-6B preregistration: `outputs/gate6b_preregistration.json`.
- The preregistration freezes source/corpus/mapping identities, masks, seeds, checkpoints, hyperparameters, corruption meaning, axes, evaluator, score targets, runtime, and raw comparison fields. It intentionally sets no pass tolerance before observing Gate-6B results.

Only unresolved ambiguity: historical Python/package/CUDA/driver versions and exact A100 SKU were not preserved.

## Proposed next gate

**PHASE 2 GATE 6B — E3 CANONICAL FRESH TRAINING AND FIDELITY EVALUATION**

Gate 6B has not begun.
