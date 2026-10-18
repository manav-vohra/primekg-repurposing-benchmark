# Phase 2 Gate 1: artifact and provenance validation

The clean validator reads [`artifacts/registry.json`](../artifacts/registry.json) as its contract. Expected hashes, sizes, CSV columns, row counts, metadata, dependencies, and four ordered-axis fingerprints live there. The axis fingerprints were derived from the hash-verified frozen files; they are not claimed to be independent historical hashes. The validator puts observed hashes and findings only in its report.

The repository includes byte-identical copies of the supplied small benchmark, reference, audit, and recovered-contract files in `artifacts/frozen/`. These are read-only reference inputs. Raw PrimeKG and large model files are registered at `raw/kg.csv` and `external/<filename>` relative to the data root. Drive IDs are locators, not proof of a local copy. Historical source and notebook entries point to the original archives and are classified separately from the clean runtime.

## Use

With the package installed (`pip install -e .`):

```text
primekg-repurpose validate --tier smoke
primekg-repurpose validate --tier reference --json-report gate1-report.json
primekg-repurpose validate --tier full-local --data-root /path/to/data-root --json-report gate1-full-report.json
```

Without installing, set `PYTHONPATH=src` and run `python -m primekg_repurposing validate ...`. The command accepts an explicit `--data-root`, then `PRIMEKG_DATA_ROOT`, then defaults to `artifacts/frozen`. Supply a data root with `benchmark/`, `reference_results/`, `recovered_contracts/`, `audits/`, `raw/`, and `external/` subdirectories. An explicit `--data-root` takes priority. The command returns a nonzero exit code when a required artifact fails validation. The JSON report contains no absolute paths.

| Tier | Scope | Large files required? |
|---|---|---:|
| SMOKE | Tiny committed fixture, corruption tests | No |
| REFERENCE | Supplied small frozen and reference files | No |
| FULL_LOCAL | REFERENCE plus registered raw graph, corpora, scores, checkpoints when supplied | Yes; missing required files fail |

The validator streams SHA-256 and raw CSV rows; it never loads the 982 MB graph into memory. Expert matrix checks are CPU only. When a score NPZ is supplied, NumPy reads its `scores`, `disease_ids`, and `drug_ids` arrays to check shape and both axes. Install the optional `full` dependency for that local check. Checkpoints are hashed as files; they are not loaded into a model or GPU.

## States and safe consumption

`FOUND_AND_VERIFIED` means a local file has a matching historical hash and passes its applicable schema and axis checks. `FOUND_HASH_MISMATCH` means a local file differs from the expected bytes. `FOUND_VALIDATION_FAILURE` covers parse, schema, order, and invariant errors. `UNKNOWN_HASH` means a local file was parsed but no historical hash exists, so it is not verified. `REGISTERED_EXTERNAL_NOT_LOCAL` means a known or referenced object is not in the data root. `MISSING_REQUIRED` means the selected tier needs that file and cannot find it.

The report also records `hash_state`, `schema_state`, `axis_state`, `invariant_state`, `safe_to_consume`, expected and observed sizes/hashes, provenance class, location, Drive ID when known, producer, dependencies, consumers, timestamp, and repository commit when available. `safe_to_consume` is true only for a verified local file whose applicable checks pass. Overall `PARTIAL` is expected in REFERENCE because historical archives and large external objects remain registered but unbundled. It is not treated as a generic PASS.

The provenance classes include raw external input, historical source, diagnosed defective historical source, forensic reconciliation, corrective historical source, frozen benchmark/reference/model artifacts, recovered artifacts, reconstructed notebook snapshot, clean output, generated artifact, and found external object. Cell 19, Cell 19A, and Cell 19B remain distinct registry records. The reconstructed notebook is explicitly marked as a reconstruction, not an original Drive revision.

## Current validation and remaining provenance

The REFERENCE run verifies 50 local files and records 73 nonlocal entries: 36 Drive-indexed large objects, 25 source/archive entries, and 12 historically named outputs without a supplied Drive locator. The 36 include the exact-hash `kg.csv`, two hash-identified E3 corpora, E3 pretrained checkpoints and scores, and E4 scores plus 24 fold checkpoints. Hashes not supplied for most model objects remain unknown in the registry. E3/E4 training log filenames occur in historical source but lack supplied hashes and Drive locators.

No benchmark reconstruction, masking, metrics, model training, oracle analysis, or routing is performed by this gate. The next gate in the migration plan is the validated frozen-fold masking loader and leakage checks.
