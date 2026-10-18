# Public release risk audit

| Risk | Finding | Severity | Required action before release |
|---|---|---:|---|
| Raw PrimeKG redistribution | `kg.csv` is ~982 MB and external. License/redistribution terms are not included. | High | Perform a license review; distribute a fetch/verify recipe if redistribution is not permitted |
| DrugBank-derived names/identifiers | Candidate and role tables contain DrugBank IDs/names; redistribution permission is UNKNOWN | High | Review PrimeKG/DrugBank terms and document allowed derived-data distribution |
| Checkpoint size/necessity | Many E3/E4 fold/seed checkpoints are referenced; only one ~66 MB checkpoint is listed externally | Medium | Publish only checkpoints required by a declared tier; use checksums and optional download manifests |
| Missing large artifacts | E3 corpora and score/checkpoint tensors are external | High | Provide durable, licensed storage and checksums or an authorized regeneration path |
| Machine-specific paths | `/content/drive/MyDrive/...` is pervasive in source/manifests | High | Preserve in provenance copies; replace only in clean implementation via explicit artifact root |
| Credentials/secrets | No credential, API-key, private-key, or bearer-token material found by pattern scan | Low | Add automated secret scanning; Drive file IDs are locators, not credentials, but access policy must be checked |
| Personal information | No obvious personal email/home path found in bundled content | Low | Re-scan the complete historical workspace before publishing |
| Unpublished/private recovery material | Recovered candidates include failed and forensic cells | Medium | Keep under provenance with clear non-authoritative/superseded labels; confirm publication authorization |
| Copyrighted paper artifacts | No paper PDFs observed; project prose/data licensing remains UNKNOWN | Medium | Run final license inventory and notices generation |
| Historical/clean confusion | Identical filenames and multiple E2/E4 candidates can be mistaken for canonical code | Critical | Separate immutable `provenance/` from `src/`; attach classification and hashes; never import provenance files at runtime |
| Stale intermediates | Initial Cell 36 failed; initial Cell 46 was superseded; many named outputs are missing | High | Mark failed/superseded records, do not copy into reference results, and publish a curated artifact index |
| Scientific claim drift | Utility-level E4 reimplementation passed while exact raw-logit forward reproduction failed | Critical | Label historical and fresh outputs separately and state the acceptance gate used |
| HGT-SDE / Drug-ANN contamination | Explicitly out of scope; not observed in this bundle | High if introduced | Add repository-level exclusion/documentation check |

No files were deleted or sanitized in Phase 1.

## Phase-2 additions

| Risk | Finding | Severity | Required action before release |
|---|---|---:|---|
| Notebook identity confusion | Drive filename `hgt-sde ` does not describe the internal P1 notebook; three appended recovery cells are non-historical | Critical | Publish the three notebook classifications and cell boundary explicitly; do not rename away the original locator |
| False historical-revision claim | The reconstructed 128-cell notebook is six bytes larger than the recorded Drive revision | Critical | Label it reconstructed, never byte-identical |
| Drive locator stability/access | Large artifacts are indexed by Drive ID/size but not bundled and some lack supplied hashes | High | Retrieve under authorization, hash, mirror durably, and publish access/licensing metadata |
| PrimeKG retrieval drift | PyTDC and Dataverse attempts failed historically; the working object was manually mounted | High | Require the surviving object hash; do not treat a current upstream download as equivalent without validation |
| Historical defect erasure | Cell 19's U128 truncation could be silently replaced by Cell 19B | High | Preserve 19/19A/19B separately and document the correction chain |
| Sealed evaluation leakage | Gate B META_TEST was intentionally unopened after dev failure | Critical | Keep it sealed; publication must not imply a result that was never run |
