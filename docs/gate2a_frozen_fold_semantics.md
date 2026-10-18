# Phase 2 Gate 2A: frozen fold and masking semantics

The read-only `primekg_repurposing.benchmark` layer consumes only files that the Gate-1 registry validator marked safe. It rechecks their hashes before loading to prevent reuse of a stale successful report. The frozen benchmark, role table, quarantine, fold summary, fold-label manifest, and corpus contract remain unchanged.

Run:

```text
primekg-repurpose validate --tier reference --benchmark-semantics --json-report gate2a-report.json
```

The command prints one line per fold and includes `benchmark_semantics` in the JSON report. Its status is independent of the Gate-1 `PARTIAL` overall status caused by registered external objects. A semantics failure makes the command exit nonzero.

## Frozen semantics

`CANONICAL_1HOP` is the active protocol. `TARGET_ONLY` and `STRICT_2HOP` are recognized identifiers; their clean masking methods are deferred to the robustness gate. Targets come from the ordered primary-disease fold assignment. The frozen quarantine manifest supplies distinct `TARGET` and `BUFFER` entries. A fold hides every therapeutic role pair whose disease ID is in either group. The remaining `CLEAN_INDICATION` pairs are legal training positives. Other surviving therapeutic roles remain annotated and are never silently reinterpreted as CLEAN. A disease–drug pair absent from the role table is `UNKNOWN_UNLABELED`, not a negative.

The masking operation returns a view over the original nontherapeutic graph identity. It does not remove target/buffer disease nodes or filter biological and ontology edges. The frozen corpus contract records 8,015,236 nontherapeutic directed triples and 85,262 removed therapeutic directed rows, which sum to the frozen 8,100,498 raw rows. The raw graph and full nontherapeutic edge list are external, so this gate validates the frozen structural contract and the view's preservation of that identity; it does not independently enumerate raw edges.

| Fold | Targets | Buffers | Legal CLEAN pairs | Surviving tested buffer exposures |
|---:|---:|---:|---:|---:|
| 0 | 93 | 109 | 6,856 | 0 |
| 1 | 93 | 125 | 6,828 | 0 |
| 2 | 92 | 83 | 6,990 | 0 |
| 3 | 92 | 118 | 7,119 | 0 |
| 4 | 92 | 110 | 6,871 | 0 |
| 5 | 92 | 99 | 7,183 | 0 |
| 6 | 92 | 120 | 7,091 | 0 |
| 7 | 92 | 146 | 6,827 | 0 |

## Direct ontology leakage scope

Historical Cell 13 constructed an adjacency from `disease_disease` rows whose two disease endpoints had indication annotations, then stored the union of direct neighbors of each fold's targets as its `BUFFER` rows. The frozen manifest does not retain each target–neighbor edge. Gate 2A tests 910 unique `(fold, buffered neighbor disease)` exposures, with multiple target–neighbor edges collapsed into one exposure. It verifies that each is hidden and that none supplies therapeutic supervision; the computed surviving count is zero in all folds. The frozen fold summary's `direct_ontology_leaks` and Cell-19B fold-label manifest's `direct_hidden_label_leaks` are also zero. This is a proof over the frozen quarantine contract, not an independent proof that the raw graph contained no omitted neighbor. Gate 2B can re-enumerate individual edges after validating the exact raw `kg.csv`.

## Regression and integrity checks

The synthetic regression uses a disease ID longer than 128 characters. It preserves the complete ID through fold membership and CLEAN masking, reproducing the correct count. This protects against the historical sequence: Cell 19's `U128` truncation, Cell 19A's forensic localization, and Cell 19B's correction. Tests inject target, buffer, and direct-neighbor exposure leaks; remove legal labels; alter fold/quarantine membership and ordering; replace nontherapeutic structure; and check unknown-pair semantics. The frozen integration test checks all eight counts and zero surviving tested exposures. Gate-1 hashes reject mutated frozen files before loading.

Gate 2A validates the interpretation of frozen artifacts. It does not rebuild folds, quarantine, role labels, or the benchmark from raw PrimeKG.
