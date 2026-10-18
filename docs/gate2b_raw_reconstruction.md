# Gate 2B: raw PrimeKG → frozen P1-v0 benchmark

The `reconstruct-benchmark` command independently produces the P1 Track A v0 benchmark from the exact canonical `kg.csv`. It resolves `raw/kg.csv` through the Gate-1 registry and data root (or an explicit `--raw-kg` locator), verifies size and SHA-256 **before** scientific processing, and writes only to a separate generated directory. It refuses an output directory that overlaps the frozen reference root. Frozen files are read only for equivalence comparison and are checked against their registry hashes.

For the locally found canonical file:

```text
primekg-repurpose reconstruct-benchmark --raw-kg C:\Users\abort\Downloads\kg.csv --json-report outputs\gate2b_reconstruction.json
```

The default generated directory is `artifacts/generated/benchmark_reconstruction/`. Install `.[reconstruct]` for pandas and NumPy. Without an exact local raw file, the command returns `MISSING_RAW_INPUT`; a wrong hash returns `RAW_HASH_MISMATCH`, both before creating benchmark outputs. The full-local integration test is opt-in with `PRIMEKG_FULL_LOCAL_RAW` set to the exact raw file; ordinary CI uses small synthetic fixtures.

## Historical stage and ordering lineage

| Clean stage | Historical cells | Ordering or identity rule |
|---|---|---|
| Graph census and therapeutic canonicalization | 2–3 | Raw encounter order supplies first canonical pair/name; reverse direction is normalized to drug→disease, then relation/drug/disease duplicates are removed. |
| Candidate universes | 9–10 | All raw drug nodes form U0, independent of labels; canonical output is lexical `drug_id` order. U1/U2 use only nontherapeutic evidence. Drug name is lexical minimum of encountered variants. |
| Pair roles and primary cohort | 11 | Pair labels are sorted tuples after groupby drug/disease; disease eligibility is independently derived from ≥3 CLEAN pairs. No unobserved pair becomes a negative. |
| Disease evidence, folds | 5, 12 | Nonontology neighbor counts use unique typed neighbors; sorted strata, `numpy.RandomState(42)` shuffles, then least-loaded fold cycles assign each disease. No frozen fold assignment is read by the producer. |
| Quarantine, training counts, freeze | 12–13 | Raw `disease_disease` edges with indication-annotated endpoints supply direct adjacency. Targets and buffers are distinct; each group is written in lexical disease-ID order. Primary diseases are sorted by fold/ID, roles and truth by disease/drug. |

All therapeutic supervision for target and buffer diseases is hidden; nontherapeutic graph evidence is not deleted. The raw-edge leakage audit tests 1,074 directed target–neighbor adjacency incidences under the historical indication-annotated ontology rule and finds zero surviving visible incidences. Multiple target–neighbor incidences can collapse to one buffered disease; the frozen Gate-2A audit counted 910 unique fold–buffer exposures. Neither number asserts the absence of unrelated leakage channels.

## Verified result

Raw SHA-256: `0a5a010fcd88dcec572a573d98c26c1c244a11567092b6161d3ded611cfb5c69`. The raw graph has 8,100,498 directed rows, 4,050,249 reciprocal conceptual relations, 129,312 raw typed entity keys, and 27 retained nontherapeutic relation types. The historically reported 129,307 entities is the *retained nontherapeutic/benchmark vocabulary*, not the all-raw typed-node count; the reconstruction obtains that count independently after excluding therapeutic-only entities and forcing benchmark nodes, as in Cell 19's vocabulary census. The exact raw hash and frozen per-type census independently anchor graph identity.

Directed therapeutic rows / canonical relation-pairs are: indication 18,776 / 9,388; contraindication 61,350 / 30,675; off-label use 5,136 / 2,568. Global roles are CLEAN_INDICATION 9,177, CONTRAINDICATION_ONLY 30,552, OFFLABEL_ONLY 2,407, AMBIGUOUS_INDICATION 211, CONFLICTING_NONINDICATION 36. Candidate universes are U0 7,957, U1 7,828, U2 6,282. The independently derived primary cohort has 738 diseases and 8,368 CLEAN truth pairs.

Fold sizes: `93, 93, 92, 92, 92, 92, 92, 92`. Buffer sizes: `109, 125, 83, 118, 110, 99, 120, 146`. Legal CLEAN counts: `6856, 6828, 6990, 7119, 6871, 7183, 7091, 6827`. The generated candidate and disease axes, fold/quarantine membership, and all six benchmark CSVs match the frozen references byte-for-byte.

The generated `p1_primary_metric_policy.json` is also byte-identical. The generated benchmark manifest's scientific fields and internal artifact hashes are identical; its SHA differs solely because the actual runtime is Python 3.12.14 / pandas 3.0.1 / NumPy 2.3.5 instead of the frozen Python 3.13.15 / pandas 2.2.3 / NumPy 2.1.3. Replacing only that environment metadata yields the exact frozen manifest SHA-256. This is an environment-provenance difference, **not** a serialization-only difference and not a scientific discrepancy.

No benchmark reference, historical source, evaluator, or model code was changed. The next gate is **PHASE 2 GATE 3 — TIE-SAFE EVALUATOR RECONSTRUCTION + EXACT REFERENCE EQUIVALENCE**; it has not begun.
