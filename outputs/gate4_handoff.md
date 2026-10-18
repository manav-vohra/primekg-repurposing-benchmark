# Phase 2 Gate 4 — E1 weighted gene cosine

## Decision

**PASS.** The clean deterministic E1 implementation reproduces the recovered Cell-14 score archive exactly, reproduces frozen applicability exactly, and reproduces the frozen primary metric exactly through evaluator `1.1_tiesafe`.

## Exact result

- Expert: `E1_WEIGHTED_GENE_COSINE` version `1.0`
- Benchmark: `P1_TRACK_A_PRIMEKG_V0`
- Raw PrimeKG SHA-256: `0a5a010fcd88dcec572a573d98c26c1c244a11567092b6161d3ded611cfb5c69`
- Historical Cell-14 source SHA-256: `b4dc0191fc66b6f0f3927c40bd4cc375ba20ce6e99e82e085bdb5684ed1f0900`
- Candidate axis: 7,957, identical and in canonical order
- Disease axis: 738, identical and in canonical order
- Applicable diseases: 504
- Explicit abstentions: 234
- Score shape: 738 × 7,957 (`float32`)
- Scores compared: 5,872,266
- Unequal scores: 0
- Maximum score difference: 0.0
- Mean score difference: 0.0
- NaN differences: 0
- Repeated clean score computations: bitwise identical
- Clean macro Recall@50: `0.0438814176465906`
- Frozen macro Recall@50: `0.0438814176465906`
- Macro difference: 0.0
- Maximum disease-level evaluator difference: `1.2420620087993939e-15`

The tiny evaluator difference occurs only in selected tie-safe `Hit@K` probabilities and is attributable to decimal round-tripping in the frozen CSV. All stored E1 scores, Recall@K values, `primary_utility`, and the macro primary result are exact.

## Historical archive recovery

The connected artifact workflow recovered `p1_e1_weighted_gene_cosine_scores.npz` from Drive.

- Observed size: 912,904 bytes
- Observed SHA-256: `77857ea09a9031611a98cbfc4aa902c665aeb64edf9bcc2b8f789498d1f3b02f`
- Classification: `RECOVERY_TIME_OBSERVED`
- Historical-hash verification: false; no historical-time hash survives

The archive is retained under `artifacts/recovered/external/`; the provenance registry records its Drive identity, observed size, observed hash, and recovery-time classification without upgrading it to historically verified.

## Information contract implemented

E1 reads only direct `disease_protein` and `drug_protein` rows. Both edge orientations are accepted and reciprocal/duplicate rows collapse to canonical `(node, gene)` pairs. Candidate drug degrees count only frozen candidate drugs; disease degrees count all PrimeKG diseases. Profiles are binary, genes are lexicographically indexed, and weights, sparse-equivalent accumulation, norms, denominators, division, and serialized scores preserve Cell 14's `float32` behavior.

Applicability is not inferred from generic score distribution alone. It is exactly:

`disease_gene_count > 0 and positive_candidate_count > 0`

Failure produces `ABSTAIN_NO_DIRECT_GENE_PATH`.

Therapeutic labels, fold labels, evaluator truth, disease-disease ontology, phenotype relations, and oracle information do not enter scoring. Negative information-flow tests confirm that changing therapeutic or disease-ontology edges leaves E1 scores unchanged.

## Files changed

- `src/primekg_repurposing/experts/e1_gene_similarity.py` — isolated Cell-14 scorer, packaging, score comparison, and evaluator integration
- `src/primekg_repurposing/experts/__init__.py` — expert package export
- `src/primekg_repurposing/score_archive.py` — restricted reader for historical object-string NumPy axes
- `src/primekg_repurposing/gate4.py` — Gate-4 orchestration and equivalence report
- `src/primekg_repurposing/cli.py` — `reproduce-e1` command
- `src/primekg_repurposing/evaluation.py` — enriched standardized expert result and safe historical archive loading
- `src/primekg_repurposing/provenance.py` — safe score-archive validation
- `tests/test_e1_gene_similarity.py` — focused E1 and full-local regression coverage
- `artifacts/registry.json` — recovery-time E1 archive provenance
- `artifacts/recovered/external/p1_e1_weighted_gene_cosine_scores.npz` — recovered historical archive
- `outputs/gate4_e1_equivalence.json` — machine-readable Gate-4 evidence
- `outputs/gate4_handoff.md` — this completion report

No historical source or frozen reference artifact was modified. No E2, E3, E4, SBS/VBS, routing, winner, bootstrap, robustness, or oracle work was added.

## Verification

The complete suite ran 106 tests in 60.993 seconds: 106 passed, 0 failed, 0 errored, 0 skipped. This run included exact raw PrimeKG reconstruction, a genuine Gate-3 score archive, and all four full-local Gate-4 tests.

The workspace is a projectless non-Git checkout, so no implementation commit exists to record. The machine report records this explicitly and includes SHA-256 identities for the three principal clean implementation files instead.

Remaining E1 ambiguity: none scientifically. The only provenance limitation is the absence of a historical-time hash for the recovered NPZ; its hash remains correctly classified as recovery-time observed.

## Proposed next gate

**PHASE 2 GATE 5 — E2 DISEASE-PROFILE LABEL-TRANSFER EXPERT + EXACT SCORE/METRIC REPRODUCTION**

Gate 5 has not been started.
