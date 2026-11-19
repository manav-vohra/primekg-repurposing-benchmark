# PrimeKG project current state

## Active priority — CPU historical-result reproduction

The owner authorized the CPU release package after Gate 6C-A. Milestone A now
implements verified seed expectations, SBS/VBS, utility-level winner ties and the
source-confirmed paired bootstrap. Milestone B recomputes Gate A cost bounds and
labels static/Gate B evidence as historical replay. Milestone C adds the one-command
CLI, paper exports, equivalence checks and a clean analysis-only CI job.
See [README.md](../README.md) for the supported tier, evidence classes, commands
and limitations. These changes are submitted as focused, stacked review PRs;
they do not authorize merging earlier PRs or changing visibility. Licensing and
redistribution clearance remains separate. No expert retraining or sealed test
access is part of this priority.

## Historical Gate 6C-A review checkpoint — 2026-11-19

The currently authorized task is **Gate 6C-A historical input and submitted-paper
claim reconciliation**, superseding the earlier next-training instructions below.
Gate 6C-A now **PASSES for complete paper inventory and provenance accounting**, with
explicit unresolved claims and discrepancies. The exact owner-supplied 10-page
camera-ready PDF has SHA-256
`ab7e80b1d82046c7c26886710a4fb5f53884534d289d787185c1ee7fc0faff87`.
The ledger accounts for 238 claim records, 180 quantitative entries, five tables,
one figure and every scientific text block. This is not a full reproduction or
redistribution-clearance PASS.
PR #1 was merged with authorization as `4550df2`; its main CI run `44488462196`
passed. Commit `326f963` is preserved, and updated main was merged into the audit
branch without rebasing, overwriting, or discarding work.
See `outputs/gate6c_handoff.md`, `outputs/gate6c_claim_artifact_manifest.json`, and
`docs/GATE6C_REDISTRIBUTION_REVIEW.md`. PR #2 remains draft and unmerged for review.
The previous pause on aggregation was superseded by the owner's explicit CPU
reproduction priority. E3/E4 training remains outside the authorized scope.

GitHub metadata reports the repository as public; visibility was not changed.
Redistribution clearance remains unresolved, including already tracked derived
tables. Any visibility change requires owner authorization.

The sections below retain the prior milestone/training checkpoint and limitations;
their older next-task instructions are paused by this active review checkpoint.

## Validated milestones

| Milestone | Status |
|---|---|
| Phase 2 Gate 1 — artifact/provenance registry | PASS |
| Phase 2 Gate 2A — benchmark semantics | PASS |
| Phase 2 Gate 2B — benchmark reconstruction | PASS |
| Phase 2 Gate 3 — evaluator equivalence | PASS |
| Phase 2 Gate 4 — E1 reproduction | PASS |
| Phase 2 Gate 5 — E2 reproduction | PASS |
| Phase 2 Gate 6A — E3 corpus/protocol/checkpoints | PASS |
| Phase 2 Gate 6B preflight | BLOCKED_NO_SUITABLE_HARDWARE |
| Phase 2 Gate 6C-A — complete paper inventory/provenance accounting | PASS_WITH_EXPLICIT_UNRESOLVED_ITEMS; REVIEW_PENDING |

E1 and E2 reproduce their historical raw score matrices bitwise exactly. E3's corrected Cell-19B corpus and all three recovered Stage-A checkpoints are compatible with the clean ComplEx implementation; independent clean-versus-historical score probes are bitwise equal with maximum absolute difference `0.0`.

## Next scientific task

The next task is **E3 seed-0/fold-0 canonical Stage-B training pilot** on suitable CUDA hardware. Do not launch the remaining 23 jobs until the pilot's raw-score, ranking, applicability, resource, and metric-fidelity report has been reviewed.

Do not change `outputs/gate6b_preregistration.json`, historical checkpoints, frozen references, batch sizes, dtype, corruption count, epochs, or evaluator. Do not begin E4, seed aggregation, SBS/VBS, oracle analysis, or routing.

## Current limitations

- The Windows preflight used PyTorch `2.14.1+cpu`; CUDA was unavailable to PyTorch.
- Historical Python/package/CUDA/driver versions and exact A100 SKU were not preserved.
- Raw PrimeKG, recovered E3 corpora, model checkpoints, and historical score archives are intentionally excluded from Git and require separate authorized, hash-verified transfer.
- PrimeKG/DrugBank redistribution rights remain unresolved. Keep the GitHub repository private and review `docs/migration/public_release_risk_audit.md` before any upload or wider release.
- Historical evidence contains machine-specific paths. They are provenance, not portable runtime configuration.
- Existing Gate-6A history used the placeholder author email `YOUR_GITHUB_EMAIL`; do not rewrite history. The Windows publisher configures a repository-local GitHub noreply address for future commits.

## Important reports

- `outputs/gate1_handoff.md`
- `outputs/gate2a_handoff.md`
- `outputs/gate2b_handoff.md`
- `outputs/gate3_handoff.md`
- `outputs/gate4_handoff.md`
- `outputs/gate5_handoff.md`
- `outputs/gate6a_handoff.md`
- `outputs/gate6a_e3_preparation.json`
- `outputs/gate6b_preregistration.json`
- `outputs/gate6b_preflight.json`
- `outputs/gate6b_preflight_handoff.md`

## Resume in a new Codex session

1. Read this file, `outputs/gate6a_handoff.md`, `outputs/gate6b_preregistration.json`, and `outputs/gate6b_preflight_handoff.md`.
2. Verify `git status`, the current commit, and tags `phase2-gate5` and `phase2-gate6a`.
3. Verify every input against `artifacts/registry.json`; never substitute a current upstream download for a historical object without hash equivalence.
4. Run the focused E3 tests and hardware preflight.
5. If and only if CUDA hardware is suitable, execute seed 0/fold 0 under the frozen contract and stop for fidelity review.

No full Gate 6B PASS has been claimed.
