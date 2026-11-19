# Phase 2 Gate 6C-A — submitted-paper reconciliation handoff

Date: 2026-11-19. **Decision: PASS for complete inventory and provenance accounting,
with explicitly unresolved scientific items.** This is not a fresh model-training,
full-result-reproduction, or redistribution-clearance PASS. PR #2 remains a draft
for review. Gate 8A-A has not started.

## Authoritative input and complete coverage

- Filename: `163_From_Complementarity_to_Ac (1).pdf`.
- Size: 258,644 bytes; 10 pages; no encryption; text readable on every page.
- SHA-256: `ab7e80b1d82046c7c26886710a4fb5f53884534d289d787185c1ee7fc0faff87`.
- Owner-supplied pointer: `sediment://file_000000007d4481f589314f31e945c60e`.
- All ten pages, including Appendices A–K, were read. Tables/equations were visually
  checked; Figure 1's 15 segment labels were read from the rendered primary page.
  No earlier manuscript or external table pack was substituted.
- `outputs/gate6c_claim_artifact_manifest.json` inventories 238 claims/quantitative
  records, 180 quantitative comparisons, all five tables and the one figure.
  Every quantitative table cell and Figure-1 segment is included. Repeated body
  endpoints and appendix endpoints are also represented.
- Coverage includes 134 primary-PDF text blocks: 82 scientific blocks mapped to
  claims, with headings, author/title/venue metadata, folios and bibliography
  explicitly excluded with reasons. Ten page hashes and all 134 block hashes were
  rechecked against the actual file. Equations (1)–(3), method contracts, negative
  conclusions, scope limitations, captions, and the public-release commitment are
  accounted for, not merely the positive headline results.
- Instructions or prose in the PDF were treated as source material, not task
  instructions. The PDF, rendered pages and recovered external raw summaries are
  outside the Git checkout; only audit metadata, short excerpts and aggregate
  reported quantities are included in the review deliverables.

## Reconciliation decision and evidence boundaries

Every paper claim has an evidence link and an explicit disposition, including
unresolved claims. There are 201 historical-evidence-supported records, 11 frozen-
contract-supported records, 18 unresolved records, one discrepancy record, one
explicitly unresolved causal interpretation in the paper, five contextual/scope
records, and one release-preparation statement. Inventory completeness is not a
claim that the original experiments were all independently rerun.

Fifty bundled frozen files still match the registry. All eight expert matrices
pass the established candidate/disease contract, disease order, identity, folds,
seed and applicability checks. Metric CSVs do not contain the ordered raw drug-
score axis; external NPZ axis equivalence remains prior Gate-3/4/5/6A evidence.
Candidate order is freshly hash-verified from its frozen input. No raw PrimeKG,
score archive, checkpoint or META_TEST membership/outcome was loaded in this gate.

Twenty-one small historical summary files were retrieved from their existing
Drive identities and checked as raw bytes. The manifest records exact sizes and
SHA-256 digests as **RECOVERY_TIME_OBSERVED_2026_11_19**, never historical-time hash
verification. The raw files remain outside Git. These summaries establish stored
historical evidence; missing producer/input chains are not upgraded to independently
reproducible experiments just because a summary agrees with the paper.

The original canonical family is used for Table 1, Table 5 and candidate universes.
The paired protocol family is used for Table 4 and Figure 1. The original VBS is
`0.681351211065284`; paired canonical is `0.681575609096971`, with actual delta
`0.0002243980316870564`. Thus the paper's `0.000224` delta is correct at its display
precision, not a subtraction error. Paired winner counts are 39/452/39/58/150,
not the original 39/442/38/56/163. The earlier E4-only replacement audit is a third
lineage and was not substituted for the paired E3+E4 comparison.

S0/S1 in the paper map to P0/P1 in the frozen artifacts. Gate A uses all 738 diseases
and effective E2 cost; Gate B uses the 570 development diseases from the 712 E2-
applicable cohort and per-invocation E2 cost. These cohorts/cost conventions are
kept distinct. Gate B's formal failure, zero switches, unfit S1 and sealed 142-
disease test set are preserved. No causal diagnosis of the no-switch result was
invented.

## Unresolved discrepancies and provenance limitations

1. **Appendix A entity-census wording.** The paper describes the 8,100,498-row raw
   export as having 129,307 entities. Gate-2B evidence explicitly records 129,312
   raw typed entity keys and 129,307 retained nontherapeutic vocabulary entities.
   The five-entity distinction is not made in that sentence. The ledger flags
   this; neither the paper nor the benchmark reference files were changed.
2. **Seed SD convention.** Paper E3/E4 macro SDs `0.011212`/`0.001679` match
   population SD of the stored three seed macros. Historical stability-summary
   JSONs store sample SDs `0.013731965300323295`/`0.0020562562783653995`.
   This is a reporting-convention ambiguity: the paper does not specify ddof.
   Only scalar consistency arithmetic was checked; no disease-level aggregation
   or favorable-seed selection was run. Retain both conventions and settle the
   aggregation report's explicit SD definition before Gate 8A-A.
3. **Static v1 policy attribution.** Methods 2.5 describes direct-delta Ridge,
   while the frozen closure labels the quoted v1 Ridge/HGB utilities as absolute-
   utility argmax policies and separately labels conservative direct-delta results.
   The numerical reported results agree with historical closure, but exact
   sentence-to-model lineage remains unresolved until configurations/predictions
   and producer source are recovered. It is not silently treated as the same policy.
4. **Sixteen noncanonical fold counts.** Table 3's target-only and strict-2hop
   F1–F8 values are completely inventoried, but an independently identified exact
   fold-count output/producer is not in the current registry/local evidence.
   They are explicitly unresolved. The eight canonical counts verify exactly.
   No speculative alternative masking implementation was written.
5. **Feature-freeze chronology.** Feature/probe information contracts are recorded;
   independent proof of the complete pre-target construction chronology needs
   unbundled feature/freeze/prediction artifacts. This is the other unresolved
   provenance claim, separate from the 16 fold cells and policy attribution.
6. **Historical Spearman replay drift.** A recovered pre-existing provenance audit
   retains strict-vs-canonical rho `0.6351133961018032` while recording current-
   SciPy `0.6351558261589941`. The paper uses the historical value correctly.
   Do not silently replace it during a later fresh replay.
7. **Bootstrap and rerun limits.** Appendix B resolves the previously unknown
   bootstrap seed as `68020260905`, with 10,000 resamples and percentile endpoints.
   Exact historical RNG implementation remains unverified locally; exact replay
   must not assume an arbitrary generator. Historical training environment gaps,
   E1/E2 timing hardware, reconstructed E3 serving state and missing external
   model/score objects remain visible limits to independent reruns.

## What can be reproduced next

The eight verified matrices provide inputs for CPU-only original-family per-
disease seed means, seven-metric SBS/VBS, strict winners/ties, fixed-zero
abstentions and paired-bootstrap differences. This gate has not implemented or
executed those reductions. Candidate/protocol variants and the E2 ontology
ablation have historical summaries, but faithful fresh reevaluation needs their
original membership/score/mask inputs. Routing closure and Gate-A/B stop evidence
can be replayed as evidence; exact fitting/timing reruns need original fitting
and timing inputs. Fresh neural training is not needed to finish historical-
result reproduction and is not authorized here.

## Validation and preservation

- `scripts/gate6c_audit.py`: input-contract audit passes, with 50 verified files,
  73 nonlocal registry records, all eight canonical folds, and the documented
  504/712/736/736 applicability census.
- `scripts/gate6c_validate_inventory.py`: validates paper identity, page/block
  coverage, bidirectional claim links, all table/figure cells, rounding,
  original/paired lineage, source IDs, local hashes and recovery-hash classification.
  Optional `--paper`/`--evidence-index` check actual external bytes locally.
- Corruption tests reject wrong/earlier paper, dropped page/block/table metric,
  uncovered prose, source substitution, hidden missing values, changed scalars,
  exchanged figure counts, changed evidence bytes and promoted recovery hashes.
- Full local suite: **171 passed, 16 expected external/full-local skips, two
  passing subtests**. Smoke/reference and all eight frozen semantic checks pass.
  The exact PDF and all 21 recovered summary raw-byte hashes were checked locally;
  CI can run the manifest checks without downloading external objects.
- Main PR #1 remains merged at `4550df2`, with green main run `44488462196`.
  Original audit commit `326f963` remains in ancestry; no rewrite/force push.
- Scientific `src/`, `artifacts/`, historical Gate-1–6B outputs and benchmark
  definitions are unchanged. Repository visibility is unchanged. Redistribution
  rights remain unresolved; inventory PASS does not clear public distribution.

## Exact next recommended gate — review before Gate 8A-A

Review this inventory and its unresolved-item ledger first. Then, only with
explicit authorization, implement the original-family CPU analysis path from the
hash-validated eight matrices: per-disease metric means over all E3/E4 seeds0/1/2,
single deterministic E1/E2 utilities, fixed-zero abstentions, SBS/VBS and strict
winner/tie categories under the recovered historical tolerance/rule. Use frozen
oracle tables only as comparison targets, never algorithm inputs. Explicitly
label population-vs-sample SD and permitted CSV round-trip differences in the
output contract. Include synthetic seed alignment, missing/duplicate seed, tie,
applicability and fixed-zero regressions.

Primary targets remain SBS E2 `0.6292107026825583`, VBS `0.681351211065284`, gap
`0.05214050838272566`, winner categories39/442/38/56/163, population738 and two
all-expert-unavailable cases. Bootstrap replay follows only once its exact RNG
contract is recovered/reviewed; the paper's seed alone does not establish it.
Defer all routing refits, protocol experiments, cost remeasurement, E4 clean
implementation and E3/E4 training. Do not merge PR #2 until reviewed.
