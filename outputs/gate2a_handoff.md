# Phase 2 Gate 2A handoff — frozen fold/masking/leakage semantics

**Decision: PASS for the frozen P1 Track A v0 contract.** The clean, read-only loader and validator reproduce all eight `CANONICAL_1HOP` legal CLEAN counts. No E1–E4 model code, evaluator, raw benchmark reconstruction, or frozen-reference rewrite was performed.

## Files changed

- `src/primekg_repurposing/benchmark.py` — frozen benchmark loader, fold/masking views, label states, and semantic/leakage audit.
- `src/primekg_repurposing/cli.py` — `validate --benchmark-semantics` and machine-readable report integration.
- `artifacts/registry.json` — adds the frozen corpus contract counts to the existing Gate-1 integrity registry.
- `tests/test_benchmark_semantics.py` — 16 focused tests, including the historical long-ID regression and injected leaks.
- `docs/gate2a_frozen_fold_semantics.md` and `docs/migration/migration_plan.md` — scope and gate handoff documentation.
- `.github/workflows/gate1-validation.yml` — runs frozen semantic validation after registry checks.
- `outputs/gate2a_benchmark_semantics.json` — complete machine-readable result, including ordered target and buffer disease IDs per fold.
- `outputs/gate2a_handoff.md` — this handoff.

The historical source and all 50 frozen local reference files remain unchanged.

## Abstractions and invariant results

The API distinguishes ordered target assignments, ordered quarantine/buffer sets, legal CLEAN positives, excluded therapeutic labels, and an unchanged nontherapeutic graph-structure contract. Unobserved disease–drug pairs are `UNKNOWN_UNLABELED`, not negatives. `TARGET_ONLY` and `STRICT_2HOP` are recognized protocol IDs but have no speculative masking implementation; `CANONICAL_1HOP` is the active frozen protocol.

| Fold | Targets | Buffers | Legal CLEAN pairs | Target therapeutic leaks | Buffer therapeutic leaks | Surviving tested direct exposures |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 93 | 109 | 6,856 | 0 | 0 | 0 |
| 1 | 93 | 125 | 6,828 | 0 | 0 | 0 |
| 2 | 92 | 83 | 6,990 | 0 | 0 | 0 |
| 3 | 92 | 118 | 7,119 | 0 | 0 | 0 |
| 4 | 92 | 110 | 6,871 | 0 | 0 | 0 |
| 5 | 92 | 99 | 7,183 | 0 | 0 | 0 |
| 6 | 92 | 120 | 7,091 | 0 | 0 | 0 |
| 7 | 92 | 146 | 6,827 | 0 | 0 | 0 |

All remaining CLEAN pairs are retained; target and buffer therapeutic labels are excluded. Membership and scientifically relevant ordering checks pass. Masking retains target/buffer nodes and the original nontherapeutic structure identity; it does not perform node or structure deletion. The frozen corpus contract is 8,015,236 nontherapeutic directed triples and 85,262 removed therapeutic directed rows.

The direct-ontology audit tested **910 unique `(fold, buffered direct-neighbor disease)` exposures** and found **0 surviving**. This unit deduplicates multiple target–neighbor edges. The historical frozen summary and Cell-19B fold-label report also record zero direct leaks. This is a frozen-quarantine audit, not a claim that every possible graph leakage channel is absent.

## Verification and unresolved ambiguity

The full test suite passes: **34 tests**, including 16 new Gate 2A tests. The long-ID test uses a disease identifier over 128 characters and verifies exact membership and the correct legal-label count, guarding against the historical Cell 19 → 19A → 19B `U128` incident. Injected target, buffer, direct-exposure, membership, and ordering defects are detected. The reference-tier CLI validation reports 50 frozen files verified, 73 external records registered, zero integrity failures, and `benchmark_semantics.status=PASS`. Its top-level `PARTIAL` status reflects unavailable external artifacts, not a Gate 2A failure.

**Remaining limitation:** the frozen quarantine stores each fold's union of direct ontology neighbors, not the individual target–neighbor edges. The raw `kg.csv` and full nontherapeutic edge list are external. Gate 2A therefore cannot independently prove that the frozen neighbor union is complete or re-enumerate individual ontology edges; it verifies the frozen contract and that all recorded buffer exposures are masked. This limitation is explicitly carried forward.

**Exact proposed Gate 2B task:** `RAW PRIMEKG → FROZEN P1-v0 BENCHMARK RECONSTRUCTION`. Gate 2B has not begun.
