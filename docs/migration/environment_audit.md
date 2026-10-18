# Environment audit

## Observed dependencies

| Dependency | Classification | Evidence / use | Version status |
|---|---|---|---|
| Python | Required scientific runtime | All sources | Benchmark manifest says 3.13.15 for benchmark generation; expert-producing runtime UNKNOWN |
| NumPy | Required scientific | arrays, NPZ, RNG, ranking, linear algebra | Manifest says 2.1.3 for benchmark generation; expert runtime UNKNOWN |
| pandas | Required scientific | CSV schemas, joins, matrices, summaries | Manifest says 2.2.3 for benchmark generation; expert runtime UNKNOWN |
| SciPy sparse | Required scientific | E1 sparse profiles; E2 TF-IDF/cosine | UNKNOWN |
| SciPy stats | Required analysis/scientific | hypergeometric tie calculations and Spearman audits | UNKNOWN |
| PyTorch | Required scientific for E3/E4 | models, sampling, CUDA training, checkpoints | UNKNOWN for historical runs; a recovered forensic mentions a PyTorch >=2.9 API but does not prove historical version |
| CUDA/cuDNN/GPU driver | Required for historical-style E3/E4 FULL | authoritative sources require CUDA | UNKNOWN; device names and backend state are not bundled |
| `google.colab` | Colab-only infrastructure | Drive mount in E4 and later recovered analyses | Remove only at infrastructure boundary |
| pathlib, collections, hashlib, json, math, random, time, platform, os, gc, copy | Standard library | paths, provenance, RNG, timing, cleanup | Python-coupled |

No scikit-learn dependency was observed. `hypergeom` implements exact tie calculations in multiple sources and should not be replaced casually. Imports that appear redundant should be removed only after tests; this audit does not label them obsolete solely by visual inspection.

## Phase-2 exact historical observations

| Stage/fact | Value | Classification |
|---|---|---|
| Early retrieval/census Python | 3.12.13 | EXACTLY_RECORDED |
| Early NumPy / pandas / scikit-learn / PyTDC | 1.26.4 / 2.2.2 / 1.2.2 / 1.0.0 | EXACTLY_RECORDED |
| TxGNN source | `https://github.com/mims-harvard/TxGNN.git` at `0e0203c3939f7d12da27aaf10e55daaff5424023` | EXACTLY_RECORDED |
| Benchmark-generation Python / NumPy / pandas | 3.13.15 / 2.1.3 / 2.2.3 | EXACTLY_RECORDED |
| Later runtime OS/Python | Linux 6.6.122+ x86_64 glibc 2.35 / Python 3.13.15 | EXACTLY_RECORDED |
| Later PyTorch/CUDA/GPU | torch 2.11.0+cu128 / CUDA 12.8 / NVIDIA A100-SXM4-40GB (39.4935 GB) | EXACTLY_RECORDED for the later audited runtime, not automatically every original run |
| SciPy | no exact version recovered | UNKNOWN |
| cuDNN and GPU driver | no exact versions recovered | UNKNOWN |
| E3/E4 timing hardware | A100 | EXACTLY_RECORDED |
| E1/E2 timing hardware | not recorded | UNKNOWN |

The workflow spans multiple recorded runtimes. These observations must be attached to their stages; they do not justify a single fictional historical lock. scikit-learn is now confirmed in recovered routing/fitting source, so the earlier bundle-only statement that it was unobserved is superseded.

## Environment risks

- The benchmark manifest environment does not establish the environment that produced every expert result.
- GPU numerical behavior matters: Cell 43 recovered exact top-50 sets but failed its raw-logit MAE gate.
- E3 explicitly sets cuDNN deterministic/benchmark flags; E4 sources set float32 matmul precision but do not provide a complete backend snapshot.
- Seeds are present, but configuration hashes, source commits, sampling-seed records, and output hashes are incomplete in surviving outputs.

## Lock recommendation

Do not upgrade now. In Phase 2, first recover historical metadata; then create a lock file plus a container definition with Python, NumPy, pandas, SciPy, PyTorch, CUDA runtime, OS/architecture, and GPU capability pinned. Record a separate modern compatibility lock only if it passes golden behavior gates. Keep Colab adapters optional and out of the scientific core.
