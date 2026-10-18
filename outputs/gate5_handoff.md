# Phase 2 Gate 5 — E2 disease-profile label transfer

## Decision

**PASS.** The clean deterministic E2 implementation reproduces every recovered Cell-17 score exactly, reproduces historical applicability exactly, and reproduces the frozen primary metric exactly through evaluator `1.1_tiesafe`.

## Exact result

- Expert: `E2_DISEASE_PROFILE_LABEL_TRANSFER` version `1.0`
- Benchmark: `P1_TRACK_A_PRIMEKG_V0`
- Masking protocol: `CANONICAL_1HOP`
- Raw PrimeKG SHA-256: `0a5a010fcd88dcec572a573d98c26c1c244a11567092b6161d3ded611cfb5c69`
- Historical Cell-17 source SHA-256: `96607e0eacc774e9f788499bf3481a3e34bb557906eaaf68cd4586dd1c01fe2f`
- Candidate axis: 7,957, identical and in canonical order
- Disease axis: 738, identical and in canonical order
- Applicable diseases: 712
- Explicit abstentions: 26
- Score shape: 738 × 7,957 (`float32`)
- Scores compared: 5,872,266
- Unequal scores: 0
- Maximum score difference: 0.0
- Mean score difference: 0.0
- NaN mismatches: 0
- Clean and historical score archives: bitwise identical
- Clean macro Recall@50: `0.6292107026825583`
- Frozen macro Recall@50: `0.6292107026825583`
- Macro difference: 0.0
- Maximum disease-level evaluator difference: `1.0755285551056204e-15`

The tiny evaluator difference is confined to selected tie-safe `Hit@K` probabilities and results from decimal round-tripping in the frozen CSV. Stored scores, Recall@K values, `primary_utility`, and the macro primary result are exact.

## Historical archive recovery

The connected artifact workflow recovered `p1_e2_disease_profile_label_transfer_scores.npz` from Drive.

- Observed size: 1,374,036 bytes
- Observed SHA-256: `5b17c06e7e31f0e1b4dc3d63dcc3aaf0e1537b8c5c6c7bce6f1b8283a3a10eab`
- Classification: `RECOVERY_TIME_OBSERVED`
- Historical-hash verification: false; no historical-time archive hash survives
- Schema: `scores`, `disease_ids`, `drug_ids`

The archive is retained under `artifacts/recovered/external/`. The provenance registry records its connected-Drive identity, observed size, observed hash, and recovery-time classification without upgrading that hash to historically verified.

## Exact E2 information contract

E2 constructs disease profiles solely from incident nontherapeutic PrimeKG evidence. It uses these relation types:

- `disease_disease`
- `disease_phenotype_negative`
- `disease_phenotype_positive`
- `disease_protein`
- `exposure_disease`

Each feature is `relation|neighbor_type|neighbor_id`. Relation and neighbor type are encoded; edge direction is not. Reciprocal or duplicate evidence collapses to one disease-feature pair. Ontology-derived `disease_disease` features are part of the canonical representation. Therapeutic relations—indication, contraindication, and off-label use—cannot enter the profile.

The IDF corpus contains all 17,070 PrimeKG diseases with at least one usable nontherapeutic feature. It contains 36,545 features and 298,613 unique disease-feature pairs. The scoring representation contains the 738 primary query diseases and 1,362 primary-or-clean-label diseases, with 166,912 nonzero similarities.

## TF-IDF and similarity

- Term frequency: binary presence after disease-feature pair deduplication
- Document count: every PrimeKG disease with at least one incident nontherapeutic feature
- IDF: `ln((1 + N) / (1 + document_frequency)) + 1`
- IDF dtype: `float32`
- Matrix representation: SciPy CSR `float32`
- Normalization: L2
- Similarity: full cosine similarity
- Thresholding or top-k truncation: none
- Zero-profile behavior: explicit `ABSTAIN_NO_NONTHERAPEUTIC_PROFILE`

Repeated profile construction and similarity computation are bitwise identical. No random seed is scientifically required.

## Fold-legal label transfer

Positive supervision consists only of candidate-filtered `CLEAN_INDICATION` labels. For each target disease, E2 obtains the fold-specific legal pairs from the established Gate-2 benchmark mask API before transfer; it does not implement an independent fold mask and does not score globally before masking.

The consumed legal CLEAN counts are:

- fold 0: 6,856
- fold 1: 6,828
- fold 2: 6,990
- fold 3: 7,119
- fold 4: 6,871
- fold 5: 7,183
- fold 6: 7,091
- fold 7: 6,827

Target and quarantine/buffer labels are excluded before label transfer. Contraindication, off-label, ambiguous, cross-fold-illegal, and evaluation-truth labels are not positive supervision.

For each query disease and candidate drug, the exact transfer rule is:

`sum(similarity(query, legal disease) × clean label(legal disease, drug)) / sum(similarity(query, legal disease))`

Support from multiple legal diseases accumulates. There is no fitted parameter, KNN cutoff, validation tuning, or score postprocessing. Fold scoring and serialized scores use `float32`.

## Applicability

Applicability is explicit metadata, separate from all-zero score handling:

- no nontherapeutic query profile → `ABSTAIN_NO_NONTHERAPEUTIC_PROFILE`
- no positive similarity to a legal training disease, or similarity mass ≤ 0 → `ABSTAIN_NO_SIMILAR_TRAINING_DISEASE`
- no candidate receives transferable indication support → `ABSTAIN_NO_TRANSFERABLE_INDICATION`
- otherwise → `OK`

Observed statuses are 712 `OK`, 2 no-profile abstentions, and 24 no-similar-training-disease abstentions. No disease abstains for no transferable indication. This exactly reproduces 712 applicable and 26 abstaining diseases.

## Leakage and determinism regressions

All required information-flow regressions pass:

- Mutating the target disease's CLEAN labels does not change its scores.
- Mutating a buffer disease's CLEAN labels does not change target scores.
- Mutating a legal, nonzero-similarity training label changes the expected target score.
- Mutating contraindication or off-label relationships does not change positive-transfer scores.
- Injecting therapeutic graph evidence does not change disease profiles.
- Ontology features are present and affect the intended representation.
- Repeated profile CSR matrices, similarity CSR matrices, score matrices, and applicability outputs are identical.

The historical score archive is used only as an expected output for comparison. Clean scores are generated from PrimeKG nontherapeutic structure, Gate-2 mask legality, and legal CLEAN training labels, then evaluated through the Gate-3 evaluator.

## Files changed

- `src/primekg_repurposing/experts/e2_disease_transfer.py` — isolated Cell-17 profile, TF-IDF, cosine, label-transfer, applicability, and score packaging logic
- `src/primekg_repurposing/experts/__init__.py` — E2 expert exports
- `src/primekg_repurposing/gate5.py` — Gate-5 orchestration, score/evaluator comparison, determinism checks, and machine report
- `src/primekg_repurposing/cli.py` — `reproduce-e2` command
- `pyproject.toml` — optional E2 sparse-computation dependency declaration
- `tests/test_e2_disease_transfer.py` — focused and full-local Gate-5 regression coverage
- `artifacts/registry.json` — recovery-time E2 archive provenance
- `artifacts/recovered/external/p1_e2_disease_profile_label_transfer_scores.npz` — recovered historical archive
- `artifacts/generated/e2/p1_e2_disease_profile_label_transfer_scores_clean.npz` — independently generated clean score archive
- `outputs/gate5_e2_equivalence.json` — machine-readable Gate-5 evidence
- `outputs/gate5_handoff.md` — this completion report

No historical source or frozen reference artifact was modified. No E3, E4, seed aggregation, SBS/VBS, oracle, winner, bootstrap, routing, robustness-suite, figure, or final-README work was added.

## Verification

Twenty-nine E2 tests were added. The complete cross-gate suite ran 135 tests in 79.709 seconds: 135 passed, 0 failed, 0 errored, and 0 skipped. The run included the full raw PrimeKG input, recovered historical E2 scores, exact axes/applicability comparisons, all five leakage tests, deterministic reruns, and Gate-3 disease-level and macro comparisons.

The workspace is a projectless non-Git checkout, so no clean implementation commit exists. The machine report records that state explicitly and records SHA-256 identities for the principal implementation files.

Remaining E2 ambiguity: none scientifically. The only provenance limitation is the absence of a historical-time hash for the recovered NPZ. The only numerical artifact is the documented sub-`2e-15` frozen-CSV round-trip difference in selected `Hit@K` values; raw scores and the primary metric are exact.

## Proposed next gate

**PHASE 2 GATE 6 — E3 ComplEx EXPERT RECONSTRUCTION, SAVED-CHECKPOINT / SCORE EQUIVALENCE, AND TRAINING-FIDELITY VALIDATION**

Gate 6 has not been started.
