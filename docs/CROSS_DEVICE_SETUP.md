# Private cross-device setup

This project is designed to synchronize source, tests, small frozen references, provenance metadata, and completed reports through a **private** GitHub repository. Raw data, checkpoints, score archives, environments, and generated runtime outputs remain external.

## Publication safety boundary

Before first publication, read `docs/migration/public_release_risk_audit.md`. PrimeKG/DrugBank redistribution permission is unresolved, so `scripts/windows_publish.ps1` requires an explicit authorization phrase before creating or pushing a private repository. It refuses public repositories, force pushes, unrelated remotes, staged secrets, large files, checkpoint formats, raw `kg.csv`, score archives, recovered artifacts, and environments.

GitHub CLI authentication is the only unavoidable account step. The current Windows GitHub CLI token is invalid; the publisher will open the normal supported browser/device login flow and will accept only the `manav-vohra` account. Existing commits are not rewritten even though Gate 6A used a placeholder author email. Future commits use the authenticated account's GitHub noreply address when needed.

## Windows publication

From normal Windows PowerShell in the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows_publish.ps1
```

The script validates/stages the portable project, performs security and size checks, commits new synchronization tooling if necessary, preserves milestone tags, creates or verifies `primekg-repurposing-benchmark` as private, configures `origin`, pushes without rewriting history, and verifies the remote commit and privacy state.

For routine work:

```powershell
.\scripts\windows_sync.ps1 -Action start
# work, test, and commit deliberately
.\scripts\windows_sync.ps1 -Action finish
```

Both actions require a clean worktree. Pulls are fast-forward-only and pushes never use force.

## Fresh MacBook bootstrap

After the private repository exists, install GitHub CLI if needed and complete `gh auth login`. Then the one-command bootstrap shown in the completion report retrieves this private script through the authenticated GitHub API. The script clones or fast-forward-updates the checkout, creates `.venv`, installs macOS-compatible dependencies, runs reference validation and portable smoke tests, and lists all intentionally absent external objects.

Apple Silicon is supported through native Python wheels. CUDA is neither assumed nor required on macOS; Mac setup is for portable development and validation, not canonical Gate-6B GPU training.

For routine work:

```bash
bash scripts/mac_sync.sh start
# work, test, and commit deliberately
bash scripts/mac_sync.sh finish
```

## External scientific objects

Git intentionally does not contain:

- PrimeKG `kg.csv`;
- recovered E3 base/CLEAN triple archives;
- E3 Stage-A checkpoints;
- E3/E4 historical score archives;
- generated expert outputs, transfer chunks, or local environments.

Their identities, sizes, source locators, and available hashes remain in `artifacts/registry.json` and the Gate handoff reports. Transfer them only through an authorized channel and verify hashes before use. Do not use Git LFS as an implicit substitute for a licensing decision.
