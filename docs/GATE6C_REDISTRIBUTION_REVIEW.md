# Gate 6C-A tracked-file redistribution review

Audit date: 2026-11-17. GitHub reports this repository as public. No visibility,
sharing, history, or frozen file was changed. These findings identify potential
restrictions and missing permissions, not a determination that a license was violated.

## Scope and reproducible evidence

The machine-readable inventory is `outputs/gate6c_redistribution_audit.json`.
It covers all 133 files tracked at PR #1 head `1f5a78a6`, tree
`f7056568c43fd3c37d0e2cc60141ae34b0c5c554`, and marks membership in observed
main `1f528f1` (132 files). Main and PR #1 contain identical scientific artifacts;
PR #1 changes CI/test infrastructure and adds a roadmap. Audit reports/scripts
created during this session were untracked at the time of the snapshot and are
not represented as historical inputs. Each inventoried file has its byte count,
SHA-256, content-risk flags, and CSV column names where applicable. No raw rows
are copied into the inventory.

`python scripts/gate6c_redistribution_audit.py` re-audits the tracked checkout and
its `origin/main` reference; fetch remote refs first when network access is available.
A regenerated report describes that new snapshot, not automatically this baseline.
This audit does not establish legal clearance, license compatibility, ownership,
or permissions of materials merely referenced by locators. No license/notice file
was present in the inspected tree.

## Highest-priority files

| Tracked path under artifacts/frozen/ | Observed content | Concern and review needed |
|---|---|---|
| benchmark/p1_v0_candidate_drugs.csv | 7,957 DrugBank identifiers, drug names, graph-derived evidence/degrees | Verify PrimeKG distribution terms and upstream DrugBank permissions for these fields and this use |
| benchmark/therapeutic_pair_evaluation_roles.csv | Drug/disease pairs, source label sets, evaluation roles; 2,074 distinct DrugBank IDs | Derived therapeutic annotations may retain upstream restrictions; inspect field-level lineage and permissions |
| benchmark/p1_v0_primary_eval_roles.csv | Primary disease/drug role labels; 1,959 distinct DrugBank IDs | Same issue for the evaluation subset; small size does not establish permission |
| benchmark/p1_v0_primary_truth.csv | Positive therapeutic truth pairs; 1,681 distinct DrugBank IDs | Review derived-label redistribution before wider publication |
| benchmark/p1_e3_complex_entities.csv | 129,307 entity mappings including 7,957 DrugBank IDs and other source namespaces | Review the complete multi-source identifier mapping, not only DrugBank fields |
| benchmark/p1_v0_primary_diseases.csv and p1_v0_k8_quarantine_manifest.csv | Disease IDs/names, cohort/role counts, ontology-derived fold membership | Review source ontology/database attribution and derivative terms |
| reference_results/*expert_matrix*.csv and recovered_contracts/p1_p15_gateA_expected_utility_matrix_v1.csv | Disease-level results, identifiers/names, applicability and runtime fields | Aggregate scientific results and row-level derived releases may require different permissions; do not assume results inherit blanket clearance |

The sixth file matching a DrugBank ID pattern is a small synthetic test fixture;
pattern matches alone do not make it restricted. The JSON inventory retains the
exact filename and count so it can be reviewed separately.

Additional tracked contracts, graph census, mappings, audits and summaries need an
attribution/licensing inventory even where they contain no DrugBank identifier.
Eight files contain machine-specific provenance paths; four contain external
artifact locators by the audit's conservative pattern rules. These locators are not
credentials, nor proof that recipients can access the objects. No raw `kg.csv`,
checkpoint, score NPZ or external archive is tracked in the inspected tree. A
filename scan of locally available Git history also found none of these names;
this is not a full sensitive-content or remote-fork audit.

## Safest proposed remediation

1. Obtain owner authorization to make the repository temporarily private while
   redistribution rights are resolved. This is a proposal only: visibility remains
   unchanged, exactly as requested. Prior public access cannot be undone by privacy.
2. Preserve an immutable, access-controlled copy of the complete current history,
   references, hashes and evidence before considering any removal. Do not edit,
   sanitize, rename away, or overwrite the scientific reference files in place.
3. Establish field-level licenses, original attribution and notices for PrimeKG,
   DrugBank-derived content, disease ontologies and all namespaces in the entity
   mapping. Review the actual snapshot's terms; a current website license or a
   successful download does not establish rights to the historical artifact.
4. If any tracked artifact cannot be redistributed, propose an explicitly reviewed
   source-only public distribution with the original scientific files supplied
   through an authorized private data root or permitted acquisition/verification
   recipe. Keep original hashes, schema, axes and benchmark identity intact.
   Removing a file in a new commit does not remove it from public Git history.
   Any history rewrite, release removal or fork/cache cleanup needs a separate
   owner-approved plan; none was attempted here.
5. Add accurate code/data license separation, attribution, artifact access terms
   and a release checklist after the rights are established. A license chosen for
   original code must not purport to relicense upstream data. Public release
   clearance remains unresolved until these decisions are reviewed.

As of the original 2026-11-17 snapshot, no external table packs, paper PDFs, restricted data, notebooks, checkpoints or
archives were copied into the repository during this session. Local new reports
contain filenames/hashes, derived validation counts, and already tracked frozen
summary values; nothing from that audit had yet been pushed to public GitHub.
On 2026-11-19 the owner authorized submitting Gate-6C-A deliverables through normal
review. The proposed review files contain only audit metadata, reports, scripts
and synthetic tests, with no newly copied restricted row-level artifacts or paper.
Visibility and redistribution clearance remain unchanged.
