# Phase 2 Gate 2B handoff — raw PrimeKG → frozen P1-v0 benchmark

**Decision: PASS.** The independently produced P1 Track A v0 benchmark is scientifically equivalent to the frozen benchmark. The six requested CSVs and the prerequisite metric-policy JSON are byte-identical; the benchmark manifest differs only in actual software-version metadata. The exact raw file was present, hash-verified before processing, and no frozen or historical file was changed.

## Input and graph census

- Raw file: `C:\Users\abort\Downloads\kg.csv` (resolved as registry artifact `raw/kg.csv` through the explicit raw locator).
- Observed and expected SHA-256: `0a5a010fcd88dcec572a573d98c26c1c244a11567092b6161d3ded611cfb5c69`.
- 8,100,498 directed rows; 4,050,249 reciprocal conceptual relations; 27 retained nontherapeutic relation types.
- 129,312 raw typed entity keys, with the frozen per-type graph census exactly matched. The historically specified 129,307 is the retained nontherapeutic/benchmark entity vocabulary, independently reconstructed using the Cell-19 vocabulary rule; these are distinct censuses.

## Scientific reconstruction

| Relation | Directed rows | Canonical drug–disease pairs |
|---|---:|---:|
| indication | 18,776 | 9,388 |
| contraindication | 61,350 | 30,675 |
| off-label use | 5,136 | 2,568 |

| Global pair role | Count |
|---|---:|
| CLEAN_INDICATION | 9,177 |
| CONTRAINDICATION_ONLY | 30,552 |
| OFFLABEL_ONLY | 2,407 |
| AMBIGUOUS_INDICATION | 211 |
| CONFLICTING_NONINDICATION | 36 |

Pre-label candidate universes: **U0 7,957; U1 7,828; U2 6,282**. Primary cohort: **738 independently eligible diseases**, each with at least three CLEAN pairs; **8,368 primary CLEAN truth pairs**. `UNOBSERVED` remains unlabeled, not negative.

| Fold | Targets | Raw-derived buffers | Legal CLEAN training pairs | Surviving direct exposures |
|---:|---:|---:|---:|---:|
| 0 | 93 | 109 | 6,856 | 0 |
| 1 | 93 | 125 | 6,828 | 0 |
| 2 | 92 | 83 | 6,990 | 0 |
| 3 | 92 | 118 | 7,119 | 0 |
| 4 | 92 | 110 | 6,871 | 0 |
| 5 | 92 | 99 | 7,183 | 0 |
| 6 | 92 | 120 | 7,091 | 0 |
| 7 | 92 | 146 | 6,827 | 0 |

The raw ontology audit checks **1,074 directed target–neighbor adjacency incidences** under the historical indication-annotated `disease_disease` rule. No such incidence remains therapeutically visible. The independently generated quarantine CSV has the exact frozen hash, resolving Gate 2A's uncertainty about completeness of its recorded buffer union. This is the historical direct-neighbor test, not a universal graph-leakage claim. Nontherapeutic structure is retained; only therapeutic supervision is masked.

## Artifact-by-artifact equivalence

| Generated artifact | Semantic equivalence | SHA-256 equivalence | Generated SHA-256 |
|---|---|---|---|
| `p1_v0_candidate_drugs.csv` | Exact, including ordered candidate axis | Exact | `dfe7275c60b6b75b2a8fa45c017c7675e3e438d6b59722f91517ff78862c2776` |
| `p1_v0_primary_diseases.csv` | Exact, including ordered disease/fold axis | Exact | `722eec938337a73e7867d384af509d3302bf27d133b665238b76b91ec50d7932` |
| `p1_v0_primary_eval_roles.csv` | Exact | Exact | `c51481941ea30b861e538678dbd4df78fddafeedd91a77ece2de40c157255564` |
| `p1_v0_primary_truth.csv` | Exact | Exact | `e17dc6f289f2d467a693d9941f18caf38a36ef11d870f7fc1ebec71953a25b45` |
| `p1_v0_k8_quarantine_manifest.csv` | Exact, including membership and order | Exact | `d5aaaaac34cc78b7a38084c374d9c340a002de638aafd85ae650ad7d2d71a1d8` |
| `p1_v0_fold_summary.csv` | Exact | Exact | `d50d830b87aebdc81731437de6204cca25e442054dca27d687a6feadfe462912` |
| `p1_v0_benchmark_manifest.json` | All scientific fields and internal artifact hashes exact | Different; environment metadata only | `e393a66ac7d0ce9a9afa83ad635eaa849f3578acfadd2f70d64d719b9c463ca7` |
| `p1_primary_metric_policy.json` (Cell-12 prerequisite) | Exact | Exact | `e394ff95f71347c539193ad59159c1f74ce3c647f8254b00e688c12fd0c6f3af` |

The frozen manifest SHA-256 is `86b9f4f65fcc981eec8a188779d884e852815da01d9ce9b6a6733868d8a38f53`. The only JSON field difference is `software_environment`: frozen Python 3.13.15 / pandas 2.2.3 / NumPy 2.1.3 versus this run's Python 3.12.14 / pandas 3.0.1 / NumPy 2.3.5. Replacing *only* that field in the generated manifest yields the exact frozen bytes and SHA-256. No difference was dismissed as “serialization-only”; this one is proven environment provenance.

## Code, tests, and boundaries

Changed: `src/primekg_repurposing/reconstruction.py`, `src/primekg_repurposing/cli.py`, `tests/test_reconstruction.py`, `pyproject.toml`, `.github/workflows/gate1-validation.yml`, `.gitignore`, `docs/gate2b_raw_reconstruction.md`, `docs/migration/migration_plan.md`, and this report. Generated scientific artifacts are separate under `artifacts/generated/benchmark_reconstruction/`; the structured equivalence report is `outputs/gate2b_reconstruction.json`.

The full suite passes with the exact raw file: **55 tests, 0 failures**. It covers five role classes, reciprocal pairs, pre-label candidate eligibility, ≥3 CLEAN cohort derivation, deterministic folds and seed sensitivity, raw ontology buffers, masking, structure preservation, long IDs, candidate/disease axis and ordering corruption, injected graph change, missing/wrong raw hash, and the opt-in full-local frozen-equivalence run. All **22 stage-count checks** pass. Gate-1 reference validation still verifies 50 frozen local files with zero failures; 73 unrelated external/archive entries remain registered but nonlocal.

Unresolved scientific discrepancies: **none**. The manifest's software-version metadata difference is recorded above. No evaluator, expert model, routing, or downstream analysis has been implemented.

**Proposed next gate:** `PHASE 2 GATE 3 — TIE-SAFE EVALUATOR RECONSTRUCTION + EXACT REFERENCE EQUIVALENCE`. Gate 3 has not begun.
