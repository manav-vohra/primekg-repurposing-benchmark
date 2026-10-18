# Clean repository design

## Proposed layout

```text
configs/
  benchmark/p1_track_a_primekg_v0.yaml
  experts/{e1,e2,e3,e4}.yaml
  execution/{smoke,analysis_only,deterministic,full}.yaml
src/primekg_repurpose/
  data/
    artifacts.py          # paths, hashes, schemas; absorbs repeated path/SHA code
    ordering.py           # frozen ID/index arrays and alignment guards
    primekg.py            # chunked raw graph reader only
    corpus.py             # E3/E4 encoded corpus loader; construction added only after Cell 19 recovery
  benchmark/
    contract.py           # frozen counts, roles, folds, protocol identity
    roles.py              # initially loader-only; construction withheld until source recovered
    masking.py            # target/buffer masks and legal CLEAN-pair selection
    validation.py         # identity, leakage, ordering, hash gates
  evaluation/
    tiesafe.py            # one exact v1.1 tie-safe evaluator
    metrics.py            # Recall/Hit/MRR/first-hit and safety metrics
    applicability.py      # explicit expert status/abstention contract
  experts/
    base.py               # result schema, not scientific scoring
    e1_weighted_gene.py   # Cell 14 scoring only
    e2_label_transfer.py  # Cell 17 representation/similarity/transfer only
    e3_complex.py         # Cells 20/21 model, samplers, two-stage training
    e4_rgcn.py            # Cells 24/25 model/training; Cell 43 forward conventions
  analysis/
    expected_utility.py   # disease-level seed aggregation
    oracle.py             # SBS/VBS/winners/ties
    robustness.py         # only after recovered sources pass gates
    routing.py            # only after missing routing source/contracts are recovered
  provenance/
    records.py            # source/config/input/output hashes and runtime metadata
scripts/
  verify_artifacts.py
  run_smoke.py
  run_analysis.py
  run_deterministic.py
  run_full.py
tests/
  unit/
  golden/
  leakage/
  integration/
artifacts/
  manifests/
  reference_results/
provenance/
  historical_source/      # immutable hash-addressed originals
  recovered_source/       # explicitly non-authoritative candidates
  audits/
docs/
  migration/
  benchmark/
```

## Behavior absorption

- `data.artifacts`: repeated `Path`, existence, SHA-256, CSV typing, JSON/NPZ loading from every cell.
- `data.ordering`: candidate/disease mappings from E1–E4 and entity/relation mappings from E3/E4.
- `benchmark.masking`: the identical legal-label logic duplicated by E2, E3, and E4. It must consume the frozen quarantine table first; construction comes later.
- `evaluation.*`: evaluator copies in E2/E3/E4 and E1's tie-safe recomputation path.
- `experts.e1_weighted_gene`: gene degree weights and sparse weighted cosine from Cell 14.
- `experts.e2_label_transfer`: nontherapeutic tokens, binary TF-IDF, cosine, and similarity-weighted label transfer from Cell 17.
- `experts.e3_complex`: ComplEx, same-type Stage-A corruption, drug-head Stage-B corruption, fixed two-stage schedule from Cells 20/21.
- `experts.e4_rgcn`: basis R-GCN and decoder/training from Cells 24/25; forward orientation and aggregation evidence from Cell 43. Historical and recovered-reimplementation results remain separately labeled.
- `analysis.expected_utility` and `analysis.oracle`: disease-level seed means and SBS/VBS code from Cells 21/25/27.

## Boundaries deliberately deferred

`benchmark.roles` and corpus construction must not synthesize missing logic. Until benchmark-construction source and Cell 19/19B are recovered, these modules validate/load frozen artifacts only. Routing/actionability is also deferred because its source and most inputs are absent.

Dependencies should remain limited to Python, NumPy, pandas, SciPy, and PyTorch. YAML is optional; JSON/TOML is preferable if it avoids adding a parser.
