# Scientific invariant registry

The executable registry is `artifacts/manifests/scientific_invariant_registry.json`. It covers benchmark identity, masking, ordering, evaluator semantics, expert contracts, and aggregate analysis.

## Highest-priority gates

1. Frozen identities: 7,957 candidates; 738 diseases; 8,368 CLEAN truth pairs; 8 folds; split seed 42.
2. Masking: zero target/buffer therapeutic supervision and fold CLEAN counts `6856, 6828, 6990, 7119, 6871, 7183, 7091, 6827`.
3. Axis identity: candidate, disease, entity, and relation arrays must exactly match frozen order before any score comparison.
4. Evaluator: uniform expected metrics within exact-score ties; ignored roles removed; applicability comes from the expert contract.
5. Seed aggregation: average disease-level utilities across seeds 0/1/2. Never choose the best seed and never average raw scores.
6. Canonical aggregate sentinels: E2 SBS `0.6292107026825583`; four-expert VBS `0.681351211065284`; gap `0.05214050838272566`; winner counts `39/442/38/56/163`.

The registry deliberately treats the frozen disease order as an opaque sequence: unlike candidates, entities, and relations, the observed disease table is not lexicographically sorted, and its construction rule is unavailable.

## Phase-2 provenance invariants

1. Notebook class is mandatory metadata: current recovered, reconstructed pre-recovery, or extracted historical source cell.
2. The reconstructed 128-cell notebook must never be described as byte-identical to a historical Drive revision.
3. Cell 19 must fail the correct-count gate where U128 truncation occurred; only Cell 19B may produce the final E3 corpus.
4. Cell 19B fold counts must equal `6856,6828,6990,7119,6871,7183,7091,6827` and its fold-label manifest must hash to `f612dee4...43aa71`.
5. Raw reconstruction must accept only `kg.csv` SHA-256 `0a5a010f...b5c69`.
6. External E3/E4 objects remain `FOUND_EXTERNAL_NOT_BUNDLED` until retrieved and independently hashed; presence in Drive is not local validation.
7. Gate B's failed development gate is an invariant stop: META_TEST remains unopened and P1 is not retroactively fitted.
