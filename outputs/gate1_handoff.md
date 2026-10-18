# Phase 2 Gate 1 handoff

Gate 1 implementation is complete. The clean package contains a 123-record canonical registry, a read-only validator, a `primekg-repurpose validate` command, 18 focused tests, a small smoke fixture, a CPU-only CI workflow, and usage documentation. The 50 copied frozen/reference files under `artifacts/frozen/` were verified byte-for-byte against supplied hashes; the originals in the supplied archives were not changed. No benchmark or scientific algorithm was migrated.

Files created or changed: `pyproject.toml`; `.gitignore`; `.github/workflows/gate1-validation.yml`; `src/primekg_repurposing/{__init__,__main__,cli,provenance}.py`; `artifacts/registry.json`; 50 byte-identical files under `artifacts/frozen/`; `tests/test_provenance.py` and seven small fixture files plus their registry; `docs/gate1_artifact_validation.md`; `docs/migration/migration_plan.md`; and three JSON validation reports plus this handoff under `outputs/`. One-time registry assembly scripts and extracted archive inspection copies are under ignored `work/`.

## Registry and validation

`artifacts/registry.json` is the single clean-runtime source for benchmark identity, counts, evaluator version, expected hashes/sizes, schemas, axis fingerprints, provenance classes, dependencies, consumers, local paths, and external Drive IDs. The validator writes observed hashes to a report. Its states are `FOUND_AND_VERIFIED`, `FOUND_HASH_MISMATCH`, `REGISTERED_EXTERNAL_NOT_LOCAL`, `UNKNOWN_HASH`, `MISSING_REQUIRED`, and `FOUND_VALIDATION_FAILURE`. A local artifact is marked safe to consume only after its available historical hash and applicable checks pass.

The command accepts an explicit data root, then `PRIMEKG_DATA_ROOT`, then `artifacts/frozen`. It supports SMOKE, REFERENCE, and FULL_LOCAL tiers and can emit JSON. No GPU or large file is required for SMOKE, REFERENCE, or CI. Raw `kg.csv` is streamed when supplied; score NPZ axes are checked on CPU when supplied.

## Verified runs

| Run | Result |
|---|---|
| Unit tests | 18 passed, including hash corruption, counts, columns, ordered axes, metadata, unknown hash, raw CSV, external registration, and CLI exit behavior |
| SMOKE | 6 verified fixture files; 1 unknown-hash fixture; 1 registered external fixture; no failures; overall `PARTIAL` by design |
| REFERENCE | 50 frozen local files verified; 73 nonlocal records explicitly registered; no failures; overall `PARTIAL` because those records remain nonlocal |
| FULL_LOCAL on this workspace | 50 local files verified; 36 large registered external files absent and reported `MISSING_REQUIRED`; nonzero exit, as designed |
| Installed command | Editable package installation in an isolated local virtual environment succeeded; command completed REFERENCE validation |

The 73 nonlocal records consist of 36 Drive-indexed large artifacts, 25 archived source/notebook entries, and 12 historically named outputs without supplied local files or Drive locators. The 36 include canonical `kg.csv`, two E3 corpus binaries, three E3 checkpoints, three E3 score tensors, three E4 score tensors, and all 24 E4 fold checkpoints. Historical hashes are absent for most model objects, so a future local copy will remain `UNKNOWN_HASH` until independently identified and recorded; the validator will not call it verified.

## Remaining provenance and next gate

The exact raw graph and large model objects have not been supplied locally. Training-log and intermediate aggregate files named in historical source lack bundled files and hashes. A standalone historical environment lock is still incomplete. These states are visible in the registry/report; they do not block the REFERENCE tier.

The exact proposed Phase 2 Gate 2 task is a read-only frozen-fold masking loader and leakage validator. It should consume only Gate-1-validated role, disease, quarantine, and corpus contracts; verify all eight legal CLEAN counts, target/buffer therapeutic exclusion, zero direct ontology leakage, and preserved nontherapeutic structure against frozen references; and stop before any expert training or benchmark regeneration.
