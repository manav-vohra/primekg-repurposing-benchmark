# Completion audit and proposed gates

Audit date: 2026-11-17. Baseline: `main` at
`1f528f1100314a992e6b305eeb64400474e60290`.
This is a proposal for review, not authorization to execute scientific gates.
No E3 training, E4 implementation, aggregation, or routing work was started.

## Verified baseline and evidence boundaries

The four baseline commits include Gate 5 (`51bdf65`, tag `phase2-gate5`),
Gate 6A (`c4ec4ce`, tag `phase2-gate6a`), synchronization tooling (`6e0d7f7`),
and publication-probe repair (`1f528f1`). The initial checkout was clean on main.
There is no AGENTS.md in this checkout. There is one Actions workflow.

Read together: [current state](CURRENT_STATE.md), all Gate 1–6B handoffs and JSON
reports in `outputs/`, [registry](../artifacts/registry.json), source/invariant
manifests in `artifacts/manifests/`, and
[Phase-1 reconciliation](migration/phase1_reconciliation.md).
Older migration plans and handoffs describe their historical state; their proposed
next gates and statements about uncommitted work are not current completion claims.
In particular, Gate 6A is now committed even though the preflight report predates it.

| Area | Established evidence | Current limit |
|---|---|---|
| Gates 1, 2A, 2B | Registry and frozen semantics PASS; exact raw graph previously reconstructed benchmark CSVs byte-for-byte | Exact raw graph absent from this clean clone; manifest software metadata differed explicitly |
| Gate 3 | Six genuine E3/E4 score archives re-evaluated with zero disease-metric differences | Score archive digests were recovery-time observations, not surviving historical hashes; status metadata came from frozen matrices |
| Gates 4, 5 | E1/E2 raw score arrays bitwise equal; primary utilities exact | Historical archive hashes are recovery-time observed; selected Hit probabilities differ below 2e-15 from CSV round trips |
| Gate 6A | Corrected Cell-19B corpus, all three Stage-A checkpoints, strict loads and independent score probes PASS | Does not establish fresh training fidelity; some tests inspect recorded evidence rather than re-read absent objects |
| Gate 6B | Hardware preflight completed; `BLOCKED_NO_SUITABLE_HARDWARE` | Zero training updates, no pilot scores, no full Gate 6B PASS |
| E4 | Historical scores evaluated in Gate 3; historical forward/fresh-training audits preserved | No clean E4 module; raw-logit forensic audit FAIL is distinct from historical utility-fidelity PASS |
| Downstream analyses | Frozen oracle, uncertainty, observability, Gate A/B evidence survives | No clean executable aggregation/routing/robustness/figure pipeline yet |

The registry contains 123 records. This clone verifies all 50 bundled frozen files;
73 external/archive records remain nonlocal. REFERENCE is deliberately `PARTIAL`
with zero failures. FULL_LOCAL cannot be claimed here. Raw data, corpora, checkpoints,
and score NPZs were not downloaded for this audit. Historical reports are evidence
of prior runs, not new local reruns of those artifact-dependent experiments.

## Immediate CI repair

Latest inspected main run [39190687932](https://github.com/manav-vohra/primekg-repurposing-benchmark/actions/runs/39190687932)
failed in unittest discovery: 20 errors, including missing SciPy and pytest.
Its three validation commands were skipped. The reconstruction-only install was
insufficient, and unittest discovery would not execute E3's pytest functions.

The focused repair adds a pytest extra, installs reconstruct/E2/E3/test extras and
CPU PyTorch, and runs `python -m pytest tests -v -rs`. Existing scientific assertions
remain. Malformed-checkpoint fixtures use pytest temporary paths. Each absent E3
corpus explicitly skips; any present corpus still must match its original hash.
No GPU is required for these validation tests, and no training command is invoked.

Local Python 3.12.14 validation: **149 passed, 16 skipped, two subtests passed**.
The 16 skips are four Gate-4 full-local, four Gate-5 full-local, four external
checkpoint cases, two external corpus cases, one real-score evaluator integration,
and one exact-raw reconstruction. This differs from the historical 10-skip run
because that workspace had E3 external objects. All three workflow validation
commands exit zero: smoke has six verified fixtures; reference has 50 verified
files and 73 nonlocal records; all eight canonical fold semantic checks PASS.
`pip check` also passes. Local versions: NumPy 2.5.5, pandas 3.1.1, SciPy 1.18.1,
PyTorch 2.15.0+cpu, pytest 9.2.0. This is a current CI environment, not a recovered
historical training environment or a frozen reproduction lock.

See [PR #1](https://github.com/manav-vohra/primekg-repurposing-benchmark/pull/1)
for the actual GitHub Actions checks. Repair commit `f4d25912` passed
[Actions run 44116751601](https://github.com/manav-vohra/primekg-repurposing-benchmark/actions/runs/44116751601)
on Python 3.11: 149 passed, 16 skipped, two subtests passed; all three validation
steps passed with zero failures. A direct corruption probe also confirmed that a
present corpus with a wrong hash fails rather than skips. Main remains unchanged
until review/merge. The roadmap is a separate documentation commit on the same PR.

## Two independent completion paths

**A — historical-result reproduction:** validate supplied frozen matrices, recompute
analyses, reconstruct reported tables/figures and historical stop decisions, with
explicit claim-to-source and output lineage. This is CPU work and does not depend
on fresh E3/E4 training. The existing eight expert matrices and oracle references
make the core portfolio analysis feasible without external checkpoints.

**B — independent model retraining:** regenerate E3/E4 scores from graph/corpora and
training code, quantify differences from historical outputs, and record environment,
RNG, runtime and measured memory. Loading recovered Stage-A E3 checkpoints and
running Stage B is not full from-scratch E3 training. Full from-scratch training
also requires independently running Stage A. Neither B milestone is a prerequisite
for finishing A, provided the repository's advertised scope is explicit.

## Proposed numbered gates (all pending review)

The suffixes below extend the established numbering; they do not replace passed gates.

1. **Gate 6C-A — historical input and paper-claim inventory.** Confirm the submitted
   camera-ready tables/figures and map each claim to immutable source, artifact hash,
   clean producer, expected output and validation. The submitted paper is not in this
   clone, so exact coverage requires that authoritative version. Validate the eight
   bundled expert matrices, axes, roles, statuses and seeds without using oracle
   outputs as inputs. Exit: explicit supported/unsupported claim ledger, with no
   unknown historical hash silently promoted to verified.
2. **Gate 8A-A — expert aggregation and SBS/VBS/oracles.** Implement disease-level
   utility means over E3/E4 seeds 0/1/2; keep deterministic E1/E2 as single experts.
   Never average logits or choose the favorable seed. Preserve applicability,
   abstention and exact tie rules, including two diseases with no applicable expert.
   Independently reproduce SBS `0.6292107026825583`, VBS `0.681351211065284`, gap
   `0.05214050838272566`, winner/tie categories and paired bootstrap policy from
   the frozen uncertainty evidence. Exit: golden comparisons and meaningful
   synthetic tie/abstention tests, CPU command with separate generated outputs.
3. **Gate 10A-A — routing, observability and costed stop evidence.** Reconstruct
   frozen static closure, observability, Gate-A utilities and Gate-B development
   failure/stop. Recover missing fitting inputs before claiming exact refitting.
   Audit every feature for legal pre-label availability, exclusions, split identity,
   and costs charged before target decisions. Preserve zero-gain/no-safe-switch
   conclusions, unknown E1/E2 timing hardware and the unopened META_TEST. Exit:
   exact frozen closure comparisons, with replay of evidence distinguished from
   refitting. No new P1 fit or sealed-test evaluation.
4. **Gate 9A-A — robustness evidence.** Inventory corrected Cell 36 candidate
   universes, Cells 38/40 protocol results, and E4 lineage. Recover/hash missing
   intermediates or mark only those claims as historical evidence. First require
   exact canonical U0/CANONICAL_1HOP agreement. TARGET_ONLY and STRICT_2HOP currently
   have no clean masking implementation; do not relabel them as executable.
   Exit: reported robustness tables traceable to inputs, with unavailable variants
   explicitly listed. New protocol experiments belong to B and need separate review.
5. **Gate 11A-A — reproduction commands, figures and tables.** Provide an offline
   `ANALYSIS_ONLY` entry point, deterministic output directory, figure/table scripts,
   paper-to-artifact map and current tested analysis lock. Add a README, installation
   guide, minimal example, citation metadata, tier matrix, external-artifact recipe
   and troubleshooting. Distinguish current executables from historical sources.
   Exit: clean-clone CI regenerates all supported paper outputs without raw PrimeKG
   or GPU; independent comparison checks values and labels, not just file existence.
6. **Gate 11B-A — distribution and release review.** Resolve the blockers below,
   document scope/deviations, test installation and analysis from a fresh clone,
   and review licenses, secrets, personal paths, archive permissions and attribution.
   Use durable permitted storage/checksum manifests for optional artifacts. Exit:
   independent release checklist, tagged reviewed revision, explicit owner approval
   before any visibility change or public release action.
7. **Gate 6B-B — E3 Stage-B pilot and fidelity (blocked/deferred).** Preserve the
   frozen preregistration and implementation identities. Requires CUDA-enabled
   PyTorch, adequate host RAM, at least 4 GiB free VRAM as a planning floor, 8+ GiB
   recommended, preferably A100-class. These are preflight estimates, not measured
   peak-memory guarantees. Historical software/driver/A100 SKU are unknown. Run only
   seed 0/fold 0 after authorization, with fresh seed-specific Stage-A load and
   optimizers, dimension 64/float32, 80 epochs, batch 2048, 16 corruptions and frozen
   masking/evaluator. Report raw-score/rank/top-50/applicability/metric differences,
   full loss, environment, timing, peak memory and hashes. No post hoc tolerance
   selected to force PASS. Review pilot before remaining 23 jobs. Full from-scratch
   Stage A is a further separately reviewed subgate (2 epochs, batch 131072), with
   its own resource preflight; Stage-B memory estimates do not cover it.
8. **Gate 7-B — E4 reconstruction and optional retraining (not started).** Recover
   and identify the 24 fold checkpoints, sources and serialization behavior before
   implementation. Preserve two-layer 64-dimensional/4-basis/27-relation R-GCN,
   relation-specific incoming mean, right transforms, ReLU/none and drug-M-disease
   decoder semantics. Audit graph/supervision/masking separately. Historical forward
   FAIL had mean error `0.0002270696211583591` exceeding `0.0001` despite exact top-50
   sets for 93 rows. The separate fresh utility-fidelity PASS is not exact logit
   reproduction and must not replace historical E4. Exit: preregistered forward and
   utility gates with distinct lineage and measured hardware needs before training;
   no protocol-variant training justified by the forensic failure alone.

Recommended A order: 6C-A → 8A-A → 10A-A → 9A-A → 11A-A → 11B-A.
B is a separate branch of the work plan, not a dependency chain blocking A.

## Public release blockers and recommendation

GitHub metadata observed on 2026-11-17 reports **visibility: public**, contrary to
CURRENT_STATE's private-repository requirement and this task's context. No visibility
change was made in this session. The owner should resolve this discrepancy promptly;
this audit does not infer when, why or by whom visibility changed.

Release readiness is blocked by unresolved PrimeKG/DrugBank derived-data rights
(including already tracked candidate/role/entity tables), absent code/data license
and citation files, lack of a top-level README and turnkey analysis/figure commands,
incomplete paper-claim mapping, missing durable permitted artifact distribution,
and incomplete downstream clean analyses. External Drive IDs alone are not a
public retrieval guarantee. Hash identity is not redistribution permission.
Historical environment gaps, E4 raw-logit failure and sealed Gate-B test state must
remain explicit limitations, rather than being treated as fresh results.

The fastest defensible completion is to finish A on CPU using already verified small
frozen artifacts, resolve licensing in parallel, and publish only the scope that can
be independently reproduced. Document B as optional/deferred training fidelity until
suitable resources and authorization exist. Preserve all historical sources,
preregistrations, references and metric values. Do not fabricate missing robustness
or fitting artifacts, reopen META_TEST, or claim a fresh-training PASS.

Stop after the CI repair and this roadmap for owner review. None of the proposed
scientific gates above has been executed by this audit.
