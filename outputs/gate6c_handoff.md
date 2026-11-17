# Phase 2 Gate 6C-A handoff — historical input and paper-claim reconciliation

Date: 2026-11-17. **Status: BLOCKED_AUTHORITATIVE_PAPER_AND_MAIN_MERGE.**
The input-contract sub-audit passes. The paper inventory is not complete, and
full Gate 6C-A PASS is not claimed. No downstream scientific implementation or
training was started.

## Repository and CI reconciliation

Contrary to the stated merged status, GitHub reads and a fresh fetch showed PR #1
OPEN, `merged=false`, with head `1f5a78a6f90ff8b4f5d81a3d4dd013fccafb7ec5`.
`origin/main` remains `1f528f1100314a992e6b305eeb64400474e60290`.
Main's latest Actions run `39190687932` is failed. PR #1 head's Actions run
`44117485875` is successful. Do not describe main as green until the reviewed PR
is merged and its push workflow passes. No merge was performed: owner direction
was requested after discovering the contradictory status.

The PR repair still looks sound: it installs SciPy/pytest/CPU PyTorch, collects
pytest functions and unittest cases, and preserves assertions and all scientific
implementations. The local baseline rerun passes 149 tests, skips 16 intended
external/full-local cases, and passes two subtests. The new audit's corruption
checks add 10 tests for axes, metadata, folds, roles, NaNs and abstention handling.
Final full local suite: **159 passed, 16 expected skips, two subtests passed**.

The working audit branch is `audit/gate6c-historical-inputs`, based on PR #1's
reviewed head. Results below also apply to main's identical frozen scientific
files. This is not represented as a checkout of a merged, green main.

## Redistribution review before scientific work

Read `docs/GATE6C_REDISTRIBUTION_REVIEW.md` and
`outputs/gate6c_redistribution_audit.json`. All 133 baseline tracked files were
inventoried, including the 132 present on observed main. No license/notice files
were found. Priority review concerns are the DrugBank candidate/name table,
therapeutic role/truth pairs, multi-source entity mapping, ontology-derived disease
and quarantine tables, and row-level expert/utility outputs. These are potential
restrictions, not a legal finding. No raw graph, NPZ, checkpoint or archive is
tracked in this snapshot.

Safest proposed remediation: owner-approved temporary privacy, immutable private
preservation, field-level rights review, then a reviewed code/data distribution
split if needed. Merely deleting a file in a new commit does not remove prior
public exposure. No visibility change, deletion or history rewrite was performed.
No audit output or external source content was pushed publicly.

## Authoritative paper: missing prerequisite

The submitted camera-ready PDF/LaTeX/version identity was not present in the
checkout or workspace. Connected Drive searches for the title and related terms,
filename searches for NeurIPS/camera/actionability/manuscript/submission, and the
identified manuscript folder found historical August table/figure packs and
September manuscript-summary artifacts, but no confirmed submitted paper.
The manuscript folder contains only `tables` and `figures`. These materials
cannot establish final numbering, captions, appendix coverage, or exact claims.
The owner was asked for the exact submitted paper or its authoritative link.

Consequently `paper_claims`, `paper_tables`, `paper_figures` and `paper_metrics`
remain empty in the manifest, explicitly marked incomplete. This avoids inventing
paper coverage from a historical manuscript pack. No PDF or external table pack
was republished. The pending inventory must include abstract, prose, methods,
results, captions, every table cell/figure panel, appendix, negative conclusions,
limitations and all reported rounding before the gate can pass.

## Completed input reconciliation

`outputs/gate6c_input_validation.json` records fresh read-only checks:

- Gate-1 REFERENCE verifies 50 frozen files; 73 nonlocal records remain; overall
  PARTIAL with no required failure. Historical source bytes are not local merely
  because a manifest records their expected digest.
- Candidate axis: 7,957 entries; ordered-axis SHA-256
  `99cb3d5768ca203306737926c30a2890c326a6c286815b0013662ec0e86a0d63`.
- Disease axis: 738 entries; ordered-axis SHA-256
  `04aec4bee6cf0168346d9261d3dcf303692a0a92fd9eb6da75ab94bc4c660a73`.
- All eight matrices match frozen hashes, disease order, expert/version, seed,
  evaluator, primary metric and fold assignment. Available per-row truth/ignored/
  contraindication/scored-candidate/training-label counts agree with contracts.
- Applicability: E1 504; E2 712; E3/E4 736 for each of seeds 0/1/2. Status and
  applicability signatures are identical across each stochastic expert's seeds.
  Two diseases have no applicable expert. Abstention utility metrics are zero;
  missing first-event ranks use the frozen CSV's blank serialization of NaN.
- All eight canonical mask checks PASS. Legal CLEAN counts are
  6856, 6828, 6990, 7119, 6871, 7183, 7091, 6827. Recorded direct buffer
  exposures remain therapeutically hidden; raw graph completeness was not rerun.
- E1/E2 are single deterministic experts, not three duplicated seed runs.
  E3/E4 seed identities are 0/1/2; no utility means or raw-score averages computed.

Metric CSVs do not store drug score axes. Candidate-axis input integrity is freshly
verified, but external score NPZ axes are supported by prior Gate-3/4/5/6A reports,
not rechecked score bytes in this session. Applicability causation also remains
historical expert evidence, not a new derivation from absent raw data.

## Machine-readable ledger and provenance gaps

`outputs/gate6c_claim_artifact_manifest.json` provides 20 **candidate historical**
claim groups, all 50 local evidence-file hashes/producer/dependency links,
source-code registry identities and hashes, 73 nonlocal entries, evaluation
configuration references, and 302 frozen scalar targets with JSON pointers.
Values are copied as stored evidence, not newly computed results.
Each candidate claim has a null paper occurrence and explicitly unconfirmed
paper membership. No candidate is asserted to be an actual camera-ready claim.

Core portfolio means, SBS/VBS, winners, many cross-metric analyses and paired
bootstrap inputs are available from the verified matrices. They need no E3/E4
training. Exact bootstrap replay additionally needs the historical RNG/resampling
producer; knowing 10,000 replicates and CI endpoints is insufficient.

Missing or conditional inputs include the submitted paper, historical source
bytes, variant-candidate/protocol scores and results, exact winner/tie and
bootstrap producer settings, static feature/fitting/prediction/split inputs,
Gate-B prediction/addendum bytes, and historical environment/timing hardware.
Static closure, Gate-A/B summaries and stop evidence can be replayed as evidence;
this is distinct from exact refitting. Preserve E4 forward FAIL separately from
fresh utility-fidelity PASS. META_TEST remains sealed; P1 was not fitted.

The pre-existing preregistration LF/CRLF digest boundary from the completion
roadmap remains documented and unchanged; it does not authorize relaxing the
training contract or altering any frozen hash.

## Exact proposed next scope — Gate 8A-A, only after inventory review

Prerequisites: resolve PR #1/main CI; obtain/hash the submitted paper; complete
page/section/table/figure/caption-to-evidence mapping; explicitly classify unresolved
claims; owner review of the full Gate-6C-A inventory. No aggregation code has begun.

Then implement one CPU-only analysis path that reads the eight hash-validated
matrices and canonical disease axis, computes per-disease expected metric utility
for E3/E4 over all seeds 0/1/2, preserves E1/E2 single-expert utility and fixed-zero
abstentions, computes SBS/VBS and deterministic winner/tie categories under the
recovered historical rule, and compares separate generated outputs to the frozen
oracle and uncertainty targets. Never consume oracle columns as algorithm inputs.

Primary acceptance targets: SBS E2 `0.6292107026825583`, VBS
`0.681351211065284`, gap `0.05214050838272566`; winner categories 39/442/38/56/163;
full population 738 with two all-expert zero cases. Predeclare numerical/CSV
round-trip handling and tie rules before execution. Add synthetic tests for ties,
seed misalignment, missing/duplicate seeds, applicability and fixed-zero behavior.
Keep original and fresh E4 outputs in separate lineages.

Include paired bootstrap only after its exact RNG/seed/resampling contract is
recovered and reviewed; otherwise explicitly defer exact-CI replay rather than
inventing settings. Defer new routing fits, protocol robustness experiments,
cost remeasurement, full figure production and all E3/E4 training to later gates.
