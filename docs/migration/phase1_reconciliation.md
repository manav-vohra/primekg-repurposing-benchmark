# Phase-1 final provenance reconciliation

Date: 2026-10-05. This record is additive: the Phase-1 conclusions remain the audit state reached from `primekg_codex_ingest.zip`; the revised classifications below are the active baseline after reading and hash-checking `primekg_phase2_supplement.zip` and `primekg_historical_notebook_recovery.zip`. No historical source was edited and no clean implementation was started.

## Evidence identity and notebook lineage

- Phase-2 supplement ZIP SHA-256: `26425e7003163d73c470afad839ff534b13d4d9172a054360cfaa1502f1d2159`. All 16 small files match `recovered_small_files_manifest.json`.
- Historical-notebook-recovery ZIP SHA-256: `863a46f1be6d4651a922faaf5b248e3518a845909049b6fdca4ebe342f8b7379`. Both notebooks and every extracted historical cell match `recovery_manifest.json`.
- `CURRENT_RECOVERED_NOTEBOOK`: Drive ID `1kZEsfWCypL5yvNHMw8o1QNMmowbMsxh4`, Drive filename `hgt-sde `, internal identity `P1_Benchmark_Feasibility.ipynb`, 131 cells, 10,514,341 bytes, SHA-256 `704d8ea1...b2a200`. Its last three cells are October-2026 recovery/search additions, not historical research source.
- `RECONSTRUCTED_PRE_RECOVERY_SNAPSHOT`: first 128 cells, 10,295,455 bytes, SHA-256 `11c53582...ae3091`. It differs by six bytes from the recorded 10,295,449-byte Drive revision and is **not** a byte-identical historical revision.
- `HISTORICAL_SOURCE_CELLS`: extracted, hash-addressed producer cells. Their source remains intact. Cells 14, 17, 20, 21, 24, 25, and 43 are byte-for-byte identical to the seven Phase-1 authoritative exports.

## Prior-to-revised classification

| Item/stage | Phase-1 classification | Recovered evidence | Revised classification | Remaining gap | Migration consequence |
|---|---|---|---|---|---|
| Raw `kg.csv` snapshot | FROZEN_ARTIFACT_ONLY | Cells 1/1B-1E retrieval/validation attempts; external Drive object, 981,751,236 bytes, SHA-256 `0a5a010f...b5c69` | EXTERNAL_INPUT_SURVIVES; HISTORICAL_SOURCE_RECOVERED | Public acquisition endpoint failed historically; licensing and durable distribution unresolved | Fetch/copy then hash-verify; never silently substitute a newer PrimeKG snapshot |
| Graph census | producer missing | Cell 2, SHA-256 `1950d94a...b0f6` | HISTORICAL_SOURCE_RECOVERED; EXACT_RECONSTRUCTION_TEST_POSSIBLE | Clean module/test still required | Reimplement only after freezing census sentinels |
| Therapeutic canonicalization | producer missing | Cell 3, SHA-256 `fae77803...0b31`; 85,262 directed rows to 42,631 canonical relation-pairs | HISTORICAL_SOURCE_RECOVERED; FROZEN_OUTPUT_SURVIVES | Clean implementation required | Preserve orientation, deduplication, and audit outputs |
| Role classification | FROZEN_ARTIFACT_ONLY | Cell 11, SHA-256 `ff040f...fdce`; explicit CLEAN/AMBIGUOUS/CONTRA/OFFLABEL/conflict rules | HISTORICAL_SOURCE_RECOVERED; FROZEN_OUTPUT_SURVIVES; EXACT_RECONSTRUCTION_TEST_POSSIBLE | Clean implementation required | Historical semantics become the golden contract |
| Candidate universe | producer missing | Cell 9, SHA-256 `f0b3d7...713`; frozen 7,957-row output survives | HISTORICAL_SOURCE_RECOVERED; FROZEN_OUTPUT_SURVIVES; EXACT_RECONSTRUCTION_TEST_POSSIBLE | Clean implementation required | Validate exact ID order and hash |
| Primary cohort/truth/eval roles | producer missing | Cells 11-13, including Cell 13 SHA-256 `19a1bc...5f5` | HISTORICAL_SOURCE_RECOVERED; FROZEN_OUTPUT_SURVIVES; EXACT_RECONSTRUCTION_TEST_POSSIBLE | Clean implementation required | Rebuild into a temporary directory and compare all schemas/counts/hashes |
| Fold assignment and quarantine | producer missing | Cell 12 SHA-256 `560df1...bfe8`; seed 42, final K=8, stratified balanced assignment, ontology-neighbor buffer | HISTORICAL_SOURCE_RECOVERED; FROZEN_OUTPUT_SURVIVES; EXACT_RECONSTRUCTION_TEST_POSSIBLE | Byte equality may depend on recorded library behavior; semantic gate must be explicit | Preserve RandomState algorithm, disease order, quarantine semantics, and legal counts |
| Benchmark freeze | producer missing | Cell 13 writes benchmark tables, constitution and manifest | HISTORICAL_SOURCE_RECOVERED; FROZEN_OUTPUT_SURVIVES; EXACT_RECONSTRUCTION_TEST_POSSIBLE | Clean implementation required | The complete historical raw-to-freeze chain now exists |
| Tie-safe evaluator | FROZEN_ARTIFACT_ONLY / duplicated logic only | Cell 16 SHA-256 `ca0d03...97ae3`; evaluator config and recovered metric policy | HISTORICAL_SOURCE_RECOVERED; FROZEN_OUTPUT_SURVIVES; EXACT_RECONSTRUCTION_TEST_POSSIBLE | Clean implementation and golden re-evaluation required | Implement Cell-16 semantics first, without changing abstention or tie behavior |
| Primary metric policy | MISSING | Bundled `p1_primary_metric_policy.json`, SHA-256 `e394ff...f3af` matching the prior manifest | RECOVERED_FROZEN_CONTRACT | Producer prose is not a separate historical cell | Copy immutably into provenance; use as evaluation contract |
| E3 Cell 19 | missing producer | Extracted Cell 19 SHA-256 `2b140c...9012`; fixed-width `U128` truncates long composite disease IDs | HISTORICAL_SOURCE_WITH_DIAGNOSED_DEFECT | Must not be used as final corpus producer | Preserve as a regression fixture and negative provenance example |
| E3 Cell 19A | missing | Extracted Cell 19A SHA-256 `5c0499...d09d`; verifies benchmark/quarantine and localizes corruption | HISTORICAL_FORENSIC_RECONCILIATION | None as evidence; it intentionally does not overwrite outputs | Preserve its diagnosis and exact count comparison |
| E3 Cell 19B | missing | Extracted corrective Cell 19B SHA-256 `f2a2af...74187`; `dtype=str`, correct fold counts and final corpus freeze | HISTORICAL_CORRECTIVE_SOURCE_RECOVERED; EXACT_RECONSTRUCTION_TEST_POSSIBLE | Large corpora remain external | Use 19B—not 19—as the migration reference producer |
| E3 fold-label manifest | MISSING | Bundled file, SHA-256 `f612dee...aa71` | RECOVERED_FROZEN_CONTRACT | None | Add to corpus validation gate |
| E3 checkpoints/scores | missing | Three checkpoint and three score objects indexed by Drive ID and size | FOUND_EXTERNAL_NOT_BUNDLED | Copy, hash locally, and establish durable licensed storage | Do not retrain merely to replace available historical artifacts |
| E4 metadata/checkpoints/scores | mostly missing | Three bundled metadata files; all 24 fold checkpoints and three score tensors indexed by Drive ID/size | METADATA_RECOVERED; FOUND_EXTERNAL_NOT_BUNDLED | Large-object hashes absent from the supplied index; retrieve and hash | Retain historical and fresh-canonical outputs as separate lineages |
| E1/E2 source and outputs | source survived; tie-safe transition uncertain | Exact notebook cells plus Cell 16 and frozen matrices/config | SOURCE/INPUT/OUTPUT_REPRODUCIBLE; deterministic scientific rerun expected | Environment/serialization may prevent bytewise artifact equality | Golden-test numeric and status outputs; do not claim bitwise files yet |
| Portfolio/SBS/VBS | sources partial, output present | Historical Cells 27 onward plus frozen oracle and closure; SBS `0.6292107026825583`, VBS `0.681351211065284` | ANALYSIS_REPRODUCIBLE_FROM_FROZEN_MATRICES | Some robustness intermediates remain external/not bundled | Analysis tier can run without retraining |
| Static routing/observability | referenced only | Historical Cells 27-34; closure and observability summary bundled | SOURCE_RECOVERED; FROZEN_OUTPUTS_RECOVERED; ANALYSIS_REPRODUCIBLE | Exact fitting inputs/intermediates are not all bundled | Equivalence-test clean analysis; preserve zero-gain/no-switch conclusion |
| Gate A | referenced only | Historical source plus constitution, 738-row expected-utility matrix, summary | SOURCE_RECOVERED; FROZEN_OUTPUTS_RECOVERED; ANALYSIS_REPRODUCIBLE | Not every intermediate is bundled | Reproduce from frozen matrices before any clean refit |
| Gate B / costed probing | referenced only | Historical Cells 56-72; constitution, failed dev gate, P0 predictability, runtime/cost evidence | SOURCE_RECOVERED; FROZEN_OUTPUTS_RECOVERED; HISTORICAL_STOP_DECISION_REPRODUCIBLE | META_TEST remains deliberately unopened; E1/E2 timing hardware unknown | Preserve the failure/stop; do not open META_TEST or invent P1 results |

## Reconstructed historical DAG

```text
kg.csv (external, hash-identified)
  -> Cells 2-3 graph census / therapeutic canonicalization
  -> Cell 11 therapeutic evaluation roles -> CLEAN indications
  -> Cells 9,11-13 candidate universe / primary disease cohort / truth / eval roles
  -> Cell 12 K=8 fold assignment + ontology quarantine
  -> Cell 13 frozen P1-v0 benchmark manifest
       -> Cell 16 tie-safe evaluator + metric policy
       -> Cells 14/17 E1/E2
       -> Cell 19 defective corpus attempt
          -> Cell 19A forensic reconciliation
          -> Cell 19B corrective E3 corpus freeze
              -> Cells 20/21 E3 training, seed matrices, expected utility
              -> Cells 24/25 E4 training, seed matrices, expected utility
                   -> seed-level expert matrices -> disease-level expected utilities
                   -> Cells 27+ SBS/VBS, bootstrap/winners, robustness
                   -> Cells 27-34 observability/static routing
                   -> Cells 56-72 Gate A -> Gate B/costed probing
```

The full machine-readable active graph is the `phase2_reconciliation` block in `artifacts/manifests/artifact_dependency_dag.json`. The complete historical `kg.csv` to frozen P1-v0 producer chain is recovered. Reconstruction has not been executed in this task; it is now testable against frozen artifacts.

## Stage-level producer ledger

“Validate” means a frozen artifact or sentinel exists against which a later isolated rerun can be checked; it does not mean this reconciliation executed the producer.

| Stage | Historical producer | Direct input | Direct output / frozen contract | Source/output state | Validate |
|---|---|---|---|---|---:|
| Retrieval | Cells 1/1B-1E (`f74d45dd...a2f4`, `2f57573d...2199`, `7c40879b...335f`, `a3e76cb7...bd30`, 1E variants `a26e...`/`e17a...`) | PyTDC/Dataverse/manual Drive object | `kg.csv`, SHA-256 `0a5a010fcd88dcec572a573d98c26c1c244a11567092b6161d3ded611cfb5c69` | historical attempts + external surviving input | Yes |
| Graph census | Cell 2, `1950d94a...b0f6` | `kg.csv` | census/audit values | historical source; derived audit | Yes |
| Therapeutic canonicalization | Cell 3, `fae77803...0b31` | therapeutic rows from `kg.csv` | canonical pairs and audit; 85,262 directed rows -> 42,631 relation-pairs | historical source + frozen output | Yes |
| Disease/ontology/leakage audits | Cells 4-8, respectively `7e7f45...335f`, `2fbb0f...aecb`, `f2be621d...2a7`, `7beea6...ee5`, `40b941...1cf` | graph census/canonical pairs | audit tables and eligibility evidence | historical source; derived evidence | Yes, against recorded sentinels |
| Candidate universe | Cell 9, `f0b3d7...713` | `kg.csv` node/edge identities | `p1_v0_candidate_drugs.csv` | historical source + frozen 7,957-row contract | Yes |
| Cohort preparation | Cell 10, `898de8...9436` | candidates, disease audits | pre-freeze cohort tables | historical source + derived evidence | Yes |
| Role classification | Cell 11, `ff040f...fdce` | canonical therapeutic relation sets | `therapeutic_pair_evaluation_roles.csv`, CLEAN/ignored/safety labels | historical source + frozen contract | Yes |
| Fold/quarantine design | Cell 12, `560df1...bfe8` | primary-eligible diseases, CLEAN/nonontology counts, ontology adjacency | K=8 assignments, quarantine and fold summary | historical source + frozen contracts | Yes |
| Benchmark freeze | Cell 13, `19a1bc...5f5` | candidates, diseases, roles, truth, folds/quarantine | P1-v0 tables, constitution, manifest | historical source + frozen contracts | Yes |
| E1 | Cell 14 / authoritative export | `kg.csv`, frozen benchmark | scores, matrix, metadata | historical source + references | Yes |
| Tie-safe evaluator | Cell 16, `ca0d03...97ae3` | candidate set, roles, expert scores/status | evaluator config and tie-safe metrics | historical source + frozen config/policy | Yes |
| E2 | Cell 17 / authoritative export | `kg.csv`, roles/quarantine, E1 matrix | scores, matrix, preliminary oracle | historical source + references | Yes |
| E3 corpus attempt | Cell 19, `2b140c...9012` | graph + frozen benchmark | defective corpus reconstruction | diagnosed historical defect | Yes: must reproduce wrong counts in a contained regression fixture |
| E3 corpus reconciliation | Cell 19A, `5c0499...d09d` | raw graph, frozen folds/quarantine, Cell-19 result | forensic report; correct frozen counts | historical forensic source | Yes |
| E3 corpus freeze | Cell 19B, `f2a2af...74187` | graph, roles, folds/quarantine | entities, relations, base/CLEAN corpora, fold labels, corpus manifest | corrective historical source; large corpora external | Yes |
| E3 training | Cells 20/21 / authoritative exports | corrective corpora, fold labels, evaluator | 3 checkpoints, scores, seed matrices, expected utility | source survives; large objects external; matrices frozen | Yes |
| E4 training | Cells 24/25 / authoritative exports | corrective corpora, fold labels, evaluator | 24 checkpoints, 3 scores, logs, metadata, seed matrices, expected utility | source/metadata/matrices survive; large objects external | Yes |
| Expert aggregation/oracle | Cells 21/25 and later portfolio cells | E1/E2 matrices, E3/E4 seed matrices | disease-level seed means, final oracle | historical source + frozen oracle | Yes |
| SBS/VBS/bootstrap/winners | Cells 27 onward | frozen expected-utility/oracle matrix | SBS/VBS/gap, bootstrap and winner summaries | source and headline contracts survive | Yes |
| Protocol robustness | later historical cells | score archives, matrices, protocol definitions | robustness tables/results | source survives; some score/intermediate objects external | Conditional on retrieval |
| Candidate-universe robustness | Cells 36/38/40 and related cells | expert scores plus universe definitions | alternate-universe utility/status outputs | historical recovered source; incomplete local intermediates | Conditional on retrieval |
| Observability/static routing | Cells 27-34 | frozen matrices and legal static features | closure/observability summary; no safe switches | historical source + selected frozen outputs | Yes for reported closure |
| Gate A | later recovered P1.5 cells | expected-utility matrix and cost constitution | 738-row utility matrix and Gate-A summary | historical source + frozen outputs | Yes |
| Gate B/costed probing | Cells 56-72 | Gate-A result, P0 legal features, timing/cost constitution | failed development gate, P0 predictability, cost audit | historical source + frozen stop evidence | Yes; META_TEST remains sealed |

## Evaluator semantic reconciliation

Cell 16 establishes: the frozen candidate universe is the rank set; AMBIGUOUS, OFFLABEL, and CONFLICTING_NONINDICATION pairs are ignored; unobserved pairs remain rankable and are not negatives; contraindication-only pairs remain rankable and are separately measured; exact-score tie blocks use a uniform random permutation; expected Recall uses the expected positive slots, Hit uses the hypergeometric no-hit complement, first-hit rank/MRR use the exact tie recurrence; zero or negative scores remain eligible; applicability/abstention is explicit from expert status, not inferred from scores; non-OK experts receive zero Recall/Hit/contra utility and undefined rank metrics. The recovered evaluator config and metric policy agree with these rules.

## Expert reproducibility matrix

| Expert | SOURCE | INPUT | TRAINING | OUTPUT | BITWISE | SCIENTIFICALLY_EQUIVALENT_RERUN_EXPECTED |
|---|---|---|---|---|---|---|
| E1 | YES | YES, with externally retrieved hash-verified `kg.csv` | N/A—deterministic computation | YES, against score/matrix references | NOT YET ESTABLISHED | YES |
| E2 | YES | YES, with `kg.csv` and frozen fold/role artifacts | N/A—deterministic computation | YES, against score/matrix references | NOT YET ESTABLISHED | YES |
| E3 | YES, including corrective corpus source | YES; large corpora/checkpoints/scores are external | YES | YES; three seed matrices plus external scores/checkpoints | NO PROMISE—GPU/runtime details incomplete | YES |
| E4 | YES, including training and Cell-43 forensic source | YES; large corpora/checkpoints/scores are external | YES | YES; metadata/matrices and indexed scores/checkpoints | NO; Cell 43 also records a failed raw-logit MAE gate | YES at the declared utility-level fidelity gate |

`YES` denotes sufficient preserved lineage and a frozen comparison target, not that this task reran it. E3/E4 artifacts marked external must be retrieved and hashed before execution. Historical E4 and the fresh canonical reimplementation remain distinct.

## Routing/actionability dimensions

| Analysis | A source survives | B frozen outputs survive | C reproduce from frozen matrices | D rerun exact original fit | E clean equivalent/testable |
|---|---:|---:|---:|---:|---:|
| Static routing | Yes | Yes | Yes | Conditional: retrieve all fitting inputs and lock sklearn behavior | Yes |
| Observability | Yes | Yes | Yes | Conditional | Yes |
| Gate A | Yes | Yes | Yes | Conditional | Yes |
| Gate B | Yes | Yes, including formal failure | Yes, including stop decision | The stopped P0 fit is conditional; P1 was intentionally not fit | Yes, without opening META_TEST |
| Cost/timing | Yes | Yes | Yes for recorded arithmetic | No exact cross-hardware replay claim; E1/E2 hardware is unknown | Yes with newly measured timings clearly separated |

## Decision gate

1. **Which Phase-1 gaps are now fully closed?** Historical producers for graph census, therapeutic canonicalization, role classification, candidates, cohort/truth/eval roles, K=8 folds/quarantine, benchmark freeze, Cell-16 evaluator, metric policy, Cell-19 lineage, final Cell-19B E3 corpora, fold-label manifest, and historical routing/actionability source/selected frozen outputs.
2. **Which gaps genuinely remain?** Durable licensed acquisition/redistribution; local retrieval plus hashing of indexed large Drive artifacts; unrecorded SciPy/cuDNN/driver and some stage-specific environment facts; complete routing-fitting intermediates; E1/E2 timing hardware; and bytewise GPU reproducibility. No historical producer step in the raw-to-benchmark chain remains missing.
3. **Is raw PrimeKG -> frozen P1-v0 benchmark reconstruction now possible from historical source?** Yes. The complete historical producer chain survives and exact comparison to frozen outputs is possible, subject to retrieving the exact hash-identified `kg.csv`; it was not executed here.
4. **Can the tie-safe evaluator now be reconstructed from historical source?** Yes. Cell 16 plus the frozen evaluator config and recovered metric policy define the semantics and comparison targets.
5. **Are E1 and E2 exactly reproducible?** Their deterministic scientific outputs are reproducible against references; byte-for-byte serialized artifacts are not yet promised until the stage environment and serialization are locked.
6. **Are E3 and E4 scientifically rerunnable from preserved artifacts/source?** Yes, after retrieving and hashing the external corpora/checkpoints/scores. Bitwise GPU equivalence is not claimed.
7. **Can headline SBS/VBS/oracle analyses be reproduced without retraining?** Yes, from the frozen expert matrices and oracle artifacts.
8. **Can routing/actionability claims be reproduced from frozen outputs?** Yes for the reported closure, observability, Gate-A and Gate-B/stop claims; exact original refitting remains conditional on retrieving all fitting inputs and environment behavior.
9. **Is enough provenance now recovered to begin clean implementation?** Yes, provided implementation begins with validation and leaves all historical material immutable.
10. **If yes, what is the exact FIRST Phase-2 implementation gate?** Build only an artifact/provenance loader and validator that distinguishes the three notebook classes, retrieves or locates the exact `kg.csv`, verifies every available SHA-256/schema/axis/count, registers external Drive objects as `FOUND_EXTERNAL_NOT_BUNDLED`, and emits a closed validation report. No scientific transformation is implemented until this gate passes.
