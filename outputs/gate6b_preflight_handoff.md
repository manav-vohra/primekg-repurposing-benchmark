# Phase 2 Gate 6B preflight handoff

## Status

**BLOCKED_NO_SUITABLE_HARDWARE**

The seed-0/fold-0 pilot was not started. Full Gate 6B is not claimed as passing, and none of the 24 fold-training jobs has begun.

## Research protection and Git state

The repository remains on `main` at `51bdf65e705b39eb223c95dd47d96d1700c4f67b`, tagged `phase2-gate5`. Gate-6A implementation, tests, registry metadata, and reports remain uncommitted. The managed environment grants read-only access to `.git`, so no checkpoint commit was attempted.

The frozen preregistration SHA-256 is `fda5b5726babca1d53561562c27434b6e2bdbf8f0c74be06fbd695d2cc4d79a2`. Its two implementation hashes match the current files exactly. The preregistration, historical checkpoints, benchmark references, and historical score archives were not modified.

## Verification

- Focused E3 suite: **29 passed, 0 skipped**.
- Full suite: **154 passed, 10 skipped**.
- All 10 skips are expected ordinary-CI/external-data cases: four Gate-4 E1, four Gate-5 E2, one registry-indexed score archive, and one exact raw-PrimeKG reconstruction test.
- Unresolved E3 coverage represented by skips: **zero**.
- The only warnings were inability to write pytest's optional `.pytest_cache` in the managed filesystem.

Every fold was re-audited through `FrozenBenchmark.mask` using `CANONICAL_1HOP`. Legal CLEAN counts remain `6856, 6828, 6990, 7119, 6871, 7183, 7091, 6827`; target and buffer label leaks are zero in every fold. The corrected Cell-19B corpus, complete long IDs, vocabularies, nontherapeutic graph, and corruption semantics remain intact.

## Frozen training configuration

Each fold must instantiate a fresh ComplEx model, strict-load the corresponding seed's recovered Stage-A checkpoint, and construct fresh optimizers. Model weights and optimizer state must never carry between folds.

- ComplEx dimension 64; float32; no AMP, normalization, or explicit regularization.
- 80 Stage-B epochs; positive batch 2,048; 16 candidate drug-head corruptions per positive.
- Entity `SparseAdam` LR 0.002; relation `Adam` LR 0.01; default optimizer settings otherwise.
- Softplus positive/negative loss; relation gradient clip norm 5.0; entity sparse gradients not clipped.
- Fold RNG `10000 + seed*100 + fold`; historical Python/NumPy/Torch/CUDA seeding and cuDNN deterministic flags preserved.
- Candidate drug head → `clean_indication` → primary disease tail; exactly 7,957 candidates and 738 diseases.
- Evaluator `1.1_tiesafe`; no early stopping, validation tuning, favorable-seed selection, or raw-score averaging.

Cell 20/21 source and checkpoint identities cross-check the preregistration. Checkpoints remain read-only and their observed SHA-256 values are unchanged.

## Hardware feasibility

Observed environment:

- CPU: AMD Ryzen 7 3700X, 8 cores / 16 logical processors.
- RAM: 15.95 GiB total, only 1.48 GiB available at inspection.
- GPU: NVIDIA GeForce GTX 1660 SUPER, 6,144 MiB VRAM; 4,939 MiB used and 1,205 MiB free.
- Driver: 576.02; driver reports CUDA 12.9.
- PyTorch: `2.14.1+cpu`; CUDA build absent; `torch.cuda.is_available() == False`; zero visible CUDA devices.
- Disk: 14.76 GiB free on `C:`; sufficient for bounded Gate-6B outputs and not the blocker.

The current PyTorch runtime cannot use the GPU. Current free GPU and system memory are also insufficient for a controlled canonical pilot with a defensible safety margin. The request explicitly forbids silently moving to CPU or shrinking the protocol, so the pilot correctly stopped before its first update.

Static model weights are about 63.15 MiB, with roughly another 126.3 MiB upper bound for entity optimizer moments before sparse gradients, 16× negative activations, framework workspace, and scoring buffers. Peak GPU memory has not been measured. Reserve at least 4 GiB free VRAM; 8+ GiB is recommended, and A100-class hardware best matches historical provenance.

Historical frozen matrices report 13.44–14.49 seconds per fold on the historical environment, mean 13.94 seconds, and 334.47 seconds summed across all 24 fold runtimes. No runtime extrapolation is made for this machine because no CUDA pilot ran.

## Pilot and historical comparison

Pilot status: **NOT_STARTED**. Updates completed: zero. No scores or metrics were produced, and historical score values were not consumed for training.

Consequently raw-score differences, Recall@50 differences, ranking agreement, top-50 overlap, utility correlation, and applicability agreement are all **NOT PERFORMED**. The historical seed-0/fold-0 target remains 93 diseases, 92 applicable, fold macro Recall@50 `0.2998505423994268`, final loss `0.020117944971492`, and recorded fold runtime `13.911118745803831` seconds.

## Full-run plan

Use a CUDA-visible PyTorch environment with at least 4 GiB free VRAM (8+ GiB recommended), adequate host RAM, and preferably A100-class hardware. Re-run preflight there, then run only seed 0/fold 0. Review its complete loss, resource, raw-score, ranking, applicability, and metric-fidelity report before authorizing the remaining 23 independent jobs.

Organize each job under `work/gate6b/runs/seed-{seed}/fold-{fold}/` with a resolved-contract snapshot, environment/RNG record, full loss trajectory, scores, metrics, warnings, runtime, peak memory, and hashes. Write a completion marker atomically only after validation. Restart interrupted folds from the immutable Stage-A checkpoint; never carry optimizer or model state across folds.

After all approved jobs finish, compare seed-level and paired disease-level behavior, ranking stability, top-50 overlap, applicability, numerical distributions, and exact evaluator results. Do not choose a post hoc tolerance merely to produce a PASS, and do not aggregate raw score tensors across seeds.

## Recommendation

Full 24-job execution is **not justified in the current environment**. Move or recreate the frozen state on suitable CUDA hardware, preserve the preregistration and all historical artifacts, repeat the hardware check, and return with the single canonical pilot for review.

Do not begin E4, seed aggregation, SBS/VBS, oracle analysis, or routing.
