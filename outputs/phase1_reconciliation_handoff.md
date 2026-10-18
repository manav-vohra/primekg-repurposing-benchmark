# PrimeKG Phase-1 reconciliation handoff

The final provenance reconciliation is complete. The authoritative record is `docs/migration/phase1_reconciliation.md`; supporting migration documents and machine-readable manifests under `artifacts/manifests/` were updated additively so the original Phase-1 findings remain auditable.

Active conclusions:

- The historical raw `kg.csv` to frozen P1-v0 benchmark producer chain is complete and can be reconstruction-tested after the exact external `kg.csv` is retrieved and hash-verified.
- Cell 16 closes the tie-safe evaluator source gap.
- Cell 19 remains a diagnosed defective source; Cell 19A remains the forensic reconciliation; Cell 19B is the corrective final E3-corpus producer.
- Indexed Drive-resident E3/E4 objects are `FOUND_EXTERNAL_NOT_BUNDLED`, not missing.
- E1/E2 deterministic scientific outputs are reproducible; bitwise serialization is not yet promised. E3/E4 are scientifically rerunnable; bitwise GPU reproducibility is not claimed.
- Headline oracle/SBS/VBS and selected routing/actionability claims are reproducible without retraining.
- Phase 2 may begin only with the artifact/provenance loader-and-validator gate; no scientific transformation was implemented in this task.
