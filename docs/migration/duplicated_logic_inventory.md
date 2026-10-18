# Duplicated logic inventory

No extraction should occur until the listed equivalence test exists.

| Proposed shared abstraction | Current locations | Behavior that must remain identical | Risk | Required equivalence test |
|---|---|---|---|---|
| Artifact resolver + SHA verifier | All authoritative files; many recovered analyses | Fail-fast existence, expected hashes, path semantics | Medium | Fixture with valid/missing/wrong-hash files reproduces each historical failure mode |
| Benchmark loaders | E1–E4 training sources | String typing, column names, row order, ID preservation | High | Loaded candidate/disease/fold arrays exactly equal frozen order and dtype expectations |
| Canonical candidate/disease mapping | E1–E4 | Drug index and disease row correspondence | Critical | Round-trip every of 7,957 candidates and 738 diseases; compare score tensor axes |
| Quarantine/legal-label masks | E2, E3 Cells 20/21, E4 Cells 24/25, recovered protocol sources | TARGET+BUFFER hiding and legal fold counts | Critical | Fold counts `[6856,6828,6990,7119,6871,7183,7091,6827]`; zero direct leakage |
| Entity/relation mapping | E3/E4 | 129,307 entity order; 28 relation order; E4 excludes `clean_indication` and compacts to 27 | Critical | Exact table hashes, contiguous indices, and explicit 28→27 mapping equality |
| Seed/device setup | E3/E4 | Python/NumPy/Torch seeds, CUDA seeds, cuDNN and matmul settings | Critical | Same initial parameter tensors and sampled corruptions for a tiny fixed fixture |
| Corruption samplers | E3 Cells 20/21; E4 Cells 24/25 | E3 same-type Stage A; E3/E4 drug-head fold corruptions; optimization-only semantics | Critical | Snapshot sampled indices for fixed RNG states; type/candidate legality assertions |
| Tie-safe evaluator | E2/E3/E4 and recovered robustness files; E1 contains legacy + tie-safe paths | Exact-score tie expectation, ignored roles, contraindications, all-zero applicability separation | Critical | Exhaustive hand-computable tie groups plus golden 738-row matrices |
| Recall/Hit/MRR/first-hit and safety metrics | All expert/evaluation sources | Fractional expected metrics under ties; empty/abstain behavior | Critical | Golden cases at K=10/50/100 and full matrix column equality |
| Applicability/abstention contract | E1–E4, especially corrected Cell 36 | Expert-declared status precedes ranking; E3 disease 40797 seed 0 remains abstained | Critical | Frozen status/applicable vectors exact for every expert/seed; regression for disease 40797 |
| Expert matrix schema/serialization | All expert sources | Column names/order, bool/NA representation, float precision | High | Schema snapshot and semantic comparison; byte equality only where environment permits |
| Expected-utility aggregator | E3 Cell 21, E4 Cell 25, portfolio analyses | Mean per-disease utility, never raw-score mean or best-seed selection | Critical | Construct counterexample where score averaging/best seed differs; match frozen oracle columns |
| SBS/VBS/winner handling | E2 Cell 27, E3/E4 oracle code, later analyses | Macro utility, ties, fixed-zero all-expert-inapplicable diseases | High | Match SBS `0.6292107027`, VBS `0.6813512111`, winner counts 39/442/38/56/163 |
| JSON-safe metadata | E3/E4 and forensic sources | NumPy/Torch scalar conversion and stable metadata fields | Low | Round-trip representative metadata and validate schema |

Scientific computations themselves—E1 weighting, E2 TF-IDF/transfer, ComplEx training, and R-GCN message passing—remain expert-specific modules, not generic helpers.
