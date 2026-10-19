[CmdletBinding()]
param([Parameter(Mandatory = $true)][ValidateSet("start", "finish")][string]$Action)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $Root

function Run-Git([string[]]$Arguments) {
    & git @Arguments
    if ($LASTEXITCODE -ne 0) { throw "git $($Arguments -join ' ') failed; nothing was force-pushed or discarded." }
}

if (git status --porcelain) { throw "Worktree has uncommitted changes. Commit or stash them deliberately before synchronization." }
$Branch = (& git branch --show-current | Out-String).Trim()
if (-not $Branch) { throw "Detached HEAD is not supported by this synchronization helper." }
Run-Git @("fetch", "--prune", "origin")

if ($Action -eq "start") {
    Run-Git @("pull", "--ff-only", "origin", $Branch)
    Write-Host "Ready to work on $Branch at $(& git rev-parse --short HEAD)."
    exit 0
}

& git merge-base --is-ancestor "origin/$Branch" HEAD
if ($LASTEXITCODE -ne 0) { throw "Local and remote histories diverged or local is behind. Run the start action and resolve deliberately." }
Run-Git @("push", "origin", $Branch)
Run-Git @("push", "origin", "--follow-tags")
Write-Host "Pushed $Branch safely at $(& git rev-parse --short HEAD)."
