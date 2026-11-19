# PrimeKG Drug Repurposing Benchmark

CPU-only historical-result reproduction for **From Complementarity to Actionability:
Observability and Cost-Aware Routing in Drug Repurposing**, submitted to the NeurIPS
2026 AI4DD workshop. This package recomputes supported analyses from verified frozen
disease-level expert metrics. It does not retrain experts or open the sealed META_TEST.

## Install and reproduce

Use a clean Python 3.10+ environment and a clone of this repository:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[analysis]'
primekg-repurpose reproduce
```

On Windows, activate with `.venv\Scripts\Activate.ps1`. The analysis extra installs
NumPy and Matplotlib, with no PyTorch, SciPy, pandas, CUDA or external artifact
download required. Once installed, reproduction runs offline. For an installed
package outside the checkout, pass `--repository-root /path/to/checkout`.

Outputs go to ignored `work/reproduction/`. Use `--output /path/to/generated`
to choose another directory; reference/source directories are rejected.
A nonzero exit means a required identity or supported equivalence check failed.
A successful run means supported outputs pass their checks, not that every paper
experiment has been independently reproduced.

## Outputs and evidence

| Output | Evidence and scope |
|---|---|
| `table1.csv`, `.md` | Class 2: original-family expert means, applicability, population seed SD, SBS/VBS and gap |
| `table2.csv`, `.md` | Class 2 computed SBS/VBS/Gate A; class 3 static/Gate B historical summaries; cohorts/cost conventions labeled |
| `table3.csv`, `.md` | Class 1: recomputed canonical legal-label counts; class 4: unavailable target-only/strict-2hop cells left blank |
| `table4_historical.csv`, `.md` | Class 3: observed historical paired protocol summary; no variant retraining |
| `table5.csv`, `.md` | Class 2: seven-metric SBS/VBS and gaps recomputed from original matrices |
| `figure1_historical.pdf`, `.svg`, `.png` | Class 3: paired-family winner counts rendered from historical evidence; content reproduction, not byte-identical artwork |
| `core_results.json`, `disease_utilities.csv` | Class 2: full-precision seed expectations, original-family utilities, winners, explicit applicability and paired intervals |
| `gate_a.json` | Class 2: E2-default oracle cascade and supported budget points, using historical costs; no new latency measurement |
| `historical_evidence.json`, `robustness_historical.json` | Class 3: original aggregate routing/observability/stop/timing and available robustness evidence, not refits |
| `unsupported_results.json`, `LIMITATIONS.md` | Explicit class 4 results and reproduction limits |
| `equivalence_report.json`, `output_manifest.json` | Independent frozen/paper-target comparisons, evidence classes, input/code/environment provenance and output hashes |

The four evidence classes are used without upgrading historical results:

1. **Independently recomputed:** calculations from underlying benchmark contracts,
   such as legal label-mask counts, without consuming their result summaries.
2. **Reproduced from verified frozen outputs:** new reductions of hash-verified
   disease metrics (not independently regenerated expert scores or model training).
3. **Historical evidence only:** explicitly labeled snapshot replay/rendering; the
   original experiment is not rerun, even when the snapshot hash is checked.
4. **Not currently verifiable:** insufficient independent evidence or unresolved
   discrepancy. Missing cells are never fabricated from the paper's reported values.

The original canonical and paired protocol families are separate. In particular,
original VBS is `0.681351211065284`; paired canonical is `0.681575609096971`.
The Figure 1 paired counts must not replace original-family winner counts.

## Scientific contracts and checks

All eight matrices cross the existing registry/evaluator integrity boundary before
use. E1/E2 are deterministic single experts; E3/E4 use all seeds 0/1/2. Disease-level
metrics are averaged before taking the oracle maximum. Explicit abstentions remain
zero and applicable zero-valued results remain applicable. No raw logits or favorable
seeds are averaged/selected.

The registered historical notebook hash and producer-cell hashes are recorded in
`core_results.json`. They establish utility-level winner `np.isclose` tolerances
(`rtol=1e-5`, `atol=1e-12`), distinct from the evaluator's exact score ties. They also
establish the paired bootstrap: PCG64/historical `default_rng`, 10,000 replacement
resamples in batches of 500, seeds `68020260905` and `68020260906`, linear 2.5/97.5
percentiles. Both frozen intervals reproduce exactly in the tested environment.
Table 1 uses population seed SD; the core report also retains sample SD explicitly.

The pipeline compares newly calculated results to the frozen oracle only after
calculation. It then reads exported CSVs back and checks supported cells against
separately inventoried camera-ready values. Synthetic regressions cover seed order,
missing seeds, mean-before-max, exact versus utility-tolerant ties, abstentions,
paired resampling, unavailable actions, cost tie breaks and corrupted exports.

```sh
python -m pip install -e '.[analysis,test]'
python -m pytest tests/test_analysis.py tests/test_downstream.py tests/test_reproduction.py
```

The complete cross-gate suite additionally needs the reconstruction/E2/E3 extras.
CI runs it separately, and runs the reproduction tests/CLI in a clean analysis-only
job. Dataset/checkpoint-dependent tests retain their explicit intended skips.

## Limits and licensing

This is retrospective ranking analysis, not therapeutic efficacy evidence. The
package does not refit static/probe selectors, reconstruct alternate candidate
scores/protocol models, remeasure serving cost, or infer META_TEST membership.
Gate A is an oracle bound on all 738 diseases; Gate B is historical development
on 570 of the 712 E2-applicable diseases, with a sealed 142-disease test set.
Their effective-versus-per-invocation cost conventions are not interchangeable.

Remaining issues include raw-versus-retained entity census wording, static-v1 policy
attribution, feature-freeze chronology, historical protocol Spearman replay drift,
and missing noncanonical fold-count inputs. Source-confirmed bootstrap and winner
contracts now resolve those specific earlier inventory limitations; the original
inventory and historical files remain unchanged. Unsupported results are emitted
explicitly on every run. No fresh E3/E4 training is necessary for the supported tier.

**Licensing/redistribution review is separate and unresolved.** The existing tracked
PrimeKG/DrugBank-derived candidate, role, truth and entity tables require rights and
attribution review. This implementation does not grant rights to those data or assign
an unapproved blanket license. See [the redistribution review](docs/GATE6C_REDISTRIBUTION_REVIEW.md).
No raw PrimeKG, external archive, checkpoint, newly recovered raw source, or generated
disease-level result is committed by the reproduction workflow. No visibility or
history changes are part of this package. Wider release/archiving needs owner review.

The authoritative paper identity and exhaustive claim map are in
[the Gate 6C-A handoff](outputs/gate6c_handoff.md) and
[the claim-artifact manifest](outputs/gate6c_claim_artifact_manifest.json).
