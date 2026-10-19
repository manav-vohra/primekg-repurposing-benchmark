[CmdletBinding()]
param(
    [string]$ExpectedOwner = "manav-vohra",
    [string]$RepositoryName = "primekg-repurposing-benchmark",
    [string]$CommitMessage = "Fix GitHub publication repository probe"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Stop-Safely([string]$Message) {
    Write-Error $Message
    exit 1
}

function Invoke-Native([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        Stop-Safely "$Program failed with exit code $LASTEXITCODE"
    }
}

function Capture-Native([string]$Program, [string[]]$Arguments) {
    $output = & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        Stop-Safely "$Program failed with exit code $LASTEXITCODE"
    }
    return ($output | Out-String).Trim()
}

function Invoke-NativeProbe([string]$Program, [string[]]$Arguments) {
    # Windows PowerShell can promote redirected native stderr to an ErrorRecord
    # when the caller uses Stop. Expected failures must therefore be captured
    # under Continue so their exit code and HTTP status can be classified.
    $PreviousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $Output = & $Program @Arguments 2>&1
        $ExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $PreviousErrorActionPreference
    }

    return [pscustomobject]@{
        ExitCode = $ExitCode
        Output = (($Output | ForEach-Object { $_.ToString() }) | Out-String).Trim()
    }
}

function Get-GitHubHttpStatus([string]$Output) {
    $Match = [regex]::Match($Output, '(?i)HTTP(?:/[0-9.]+)?\s+(?<status>[0-9]{3})')
    if ($Match.Success) { return [int]$Match.Groups['status'].Value }
    return $null
}

function Get-RepositoryProbeDisposition([object]$Result) {
    if ($Result.ExitCode -eq 0) { return "Exists" }
    $Status = Get-GitHubHttpStatus $Result.Output
    if ($Status -eq 404) { return "Missing" }
    if ($Status -eq 401 -or $Status -eq 403) { return "Unauthorized" }
    return "Failure"
}

function Normalize-Remote([string]$Value) {
    return ($Value.Trim().ToLowerInvariant() -replace '\.git$', '' -replace '/$', '')
}

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $ProjectRoot

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Stop-Safely "Git is required. Install Git for Windows, then rerun this script."
}

$ActualRoot = (Capture-Native "git" @("rev-parse", "--show-toplevel")).Replace("/", "\")
if ([IO.Path]::GetFullPath($ActualRoot) -ne [IO.Path]::GetFullPath($ProjectRoot)) {
    Stop-Safely "This script must govern the PrimeKG repository at $ProjectRoot; Git reported $ActualRoot."
}

$Branch = Capture-Native "git" @("branch", "--show-current")
if ($Branch -ne "main") {
    Stop-Safely "Expected branch main; observed '$Branch'. Switch deliberately before publishing."
}

$Required = @(
    "artifacts/registry.json",
    "artifacts/frozen/benchmark/p1_e3_complex_corpus_manifest.json",
    "outputs/gate6a_e3_preparation.json",
    "outputs/gate6a_handoff.md",
    "outputs/gate6b_preregistration.json",
    "outputs/gate6b_preflight.json",
    "outputs/gate6b_preflight_handoff.md",
    "src/primekg_repurposing/experts/e3_complex.py",
    "src/primekg_repurposing/gate6a.py",
    "tests/test_e3_complex.py",
    "docs/CURRENT_STATE.md",
    "docs/CROSS_DEVICE_SETUP.md",
    ".gitignore",
    ".gitattributes"
)
foreach ($Path in $Required) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        Stop-Safely "Required project file is missing: $Path"
    }
}

Invoke-Native "git" @("rev-parse", "phase2-gate5^{commit}") | Out-Null

$StageRoots = @(
    ".gitignore", ".gitattributes", "pyproject.toml", ".github", "src", "tests",
    "artifacts/registry.json", "artifacts/manifests", "artifacts/frozen",
    "docs", "outputs", "scripts"
) | Where-Object { Test-Path -LiteralPath $_ }
Invoke-Native "git" (@("add", "--") + $StageRoots)

$Staged = @(git diff --cached --name-only --diff-filter=ACMR)
if ($LASTEXITCODE -ne 0) { Stop-Safely "Unable to inspect staged files." }

$ForbiddenPatterns = @(
    '(^|/)kg\.csv$',
    '(^|/)work/',
    '(^|/)artifacts/recovered/external/',
    '(^|/)artifacts/generated/',
    'p1_e3_.*_scores.*\.npz$',
    'p1_e4_.*_scores.*\.npz$',
    '\.(pt|pth|ckpt|safetensors|onnx|h5|b64|part|zip|7z|tar|gz)$',
    '(^|/)(\.venv|venv|env)/'
)
foreach ($Path in $Staged) {
    foreach ($Pattern in $ForbiddenPatterns) {
        if ($Path -match $Pattern) {
            Invoke-Native "git" @("restore", "--staged", "--", $Path)
            Stop-Safely "Refusing to publish excluded large/runtime artifact: $Path"
        }
    }
    $SizeText = Capture-Native "git" @("cat-file", "-s", ":$Path")
    if ([int64]$SizeText -gt 25MB) {
        Invoke-Native "git" @("restore", "--staged", "--", $Path)
        Stop-Safely "Refusing to publish staged file larger than 25 MiB: $Path"
    }
}

$SecretRegex = '(BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,}|xox[baprs]-[A-Za-z0-9-]{10,})'
$SecretPaths = New-Object System.Collections.Generic.List[string]
$MachinePathFiles = New-Object System.Collections.Generic.List[string]
foreach ($Path in $Staged) {
    if ($Path -eq "scripts/windows_publish.ps1" -or $Path -notmatch '\.(py|ps1|sh|md|json|toml|ya?ml|txt|csv)$') { continue }
    $Content = (& git show ":$Path" | Out-String)
    if ($LASTEXITCODE -ne 0) { Stop-Safely "Unable to scan staged file: $Path" }
    if ($Content -match $SecretRegex) { $SecretPaths.Add($Path) }
    if ($Content -match 'C:\\Users\\|/Users/|/home/') { $MachinePathFiles.Add($Path) }
}
if ($SecretPaths.Count -gt 0) {
    Stop-Safely "Potential credential material found in staged files: $($SecretPaths -join ', ')"
}

Write-Host "Pre-publication review:" -ForegroundColor Cyan
Write-Host "  - Repository will be PRIVATE."
Write-Host "  - Raw kg.csv, checkpoints, score archives, recovered data, environments, and transfer chunks are excluded."
Write-Host "  - Existing audit documents say PrimeKG/DrugBank redistribution rights are unresolved."
if ($MachinePathFiles.Count -gt 0) {
    Write-Warning "Historical evidence contains machine-specific paths in: $($MachinePathFiles -join ', ')"
}
$Authorization = Read-Host "Type AUTHORIZE PRIVATE UPLOAD only if you are authorized to upload the tracked derived/reference data to private GitHub storage"
if ($Authorization -cne "AUTHORIZE PRIVATE UPLOAD") {
    Stop-Safely "Publication cancelled without changing GitHub. Staged files remain available for inspection."
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Invoke-Native "winget" @("install", "--id", "GitHub.cli", "--exact", "--source", "winget")
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
    } else {
        Stop-Safely "GitHub CLI is missing and winget is unavailable. Install https://cli.github.com/ and rerun."
    }
}

$LoginProbe = Invoke-NativeProbe "gh" @("api", "user", "--jq", ".login")
$NeedsLogin = $LoginProbe.ExitCode -ne 0 -or $LoginProbe.Output -cne $ExpectedOwner
if ($NeedsLogin) {
    if ($LoginProbe.ExitCode -eq 0 -and $LoginProbe.Output) {
        Write-Warning "GitHub CLI is authenticated as '$($LoginProbe.Output)', not '$ExpectedOwner'."
    } else {
        Write-Warning "GitHub CLI authentication is missing, invalid, or cannot access the API."
    }
    Write-Host "A normal GitHub browser/device login for $ExpectedOwner will open." -ForegroundColor Yellow
    Invoke-Native "gh" @("auth", "login", "--hostname", "github.com", "--git-protocol", "https", "--web", "--scopes", "repo")
}
Invoke-Native "gh" @("auth", "setup-git")

$VerifiedLogin = Invoke-NativeProbe "gh" @("api", "user", "--jq", ".login")
if ($VerifiedLogin.ExitCode -ne 0) {
    Stop-Safely "GitHub authentication could not be verified after login: $($VerifiedLogin.Output)"
}
$Login = $VerifiedLogin.Output
if ($Login -cne $ExpectedOwner) {
    Stop-Safely "Authenticated GitHub account is '$Login', but this project is authorized only for '$ExpectedOwner'. Rerun and complete the browser login for the correct account."
}
$UserId = Capture-Native "gh" @("api", "user", "--jq", ".id")
$Slug = "$Login/$RepositoryName"
$ExpectedRemote = "https://github.com/$Slug"

$Email = (& git config --get user.email | Out-String).Trim()
if (-not $Email -or $Email -eq "YOUR_GITHUB_EMAIL") {
    Invoke-Native "git" @("config", "--local", "user.email", "$UserId+$Login@users.noreply.github.com")
    Write-Host "Configured repository-local Git email to the GitHub noreply address. Existing history was not rewritten."
}
$Name = (& git config --get user.name | Out-String).Trim()
if (-not $Name) { Invoke-Native "git" @("config", "--local", "user.name", $Login) }

& git diff --cached --quiet
if ($LASTEXITCODE -eq 1) {
    Invoke-Native "git" @("commit", "-m", $CommitMessage)
} elseif ($LASTEXITCODE -ne 0) {
    Stop-Safely "Unable to inspect staged changes."
} else {
    Write-Host "No new local changes required a commit."
}

& git rev-parse --verify --quiet "refs/tags/phase2-gate6a" *> $null
if ($LASTEXITCODE -ne 0) {
    Invoke-Native "git" @("tag", "-a", "phase2-gate6a", "-m", "Validated Phase 2 Gate 6A")
} else {
    $Gate6ACommit = Capture-Native "git" @("rev-list", "-n", "1", "phase2-gate6a")
    & git merge-base --is-ancestor $Gate6ACommit HEAD
    if ($LASTEXITCODE -ne 0) { Stop-Safely "Existing phase2-gate6a tag is not an ancestor of HEAD; refusing to move it." }
}

$RemoteNames = @((Capture-Native "git" @("remote")) -split "`r?`n" | Where-Object { $_ })
$Origin = ""
if ($RemoteNames -contains "origin") {
    $Origin = Capture-Native "git" @("remote", "get-url", "origin")
    if ((Normalize-Remote $Origin) -ne (Normalize-Remote $ExpectedRemote)) {
        Stop-Safely "Existing origin points to '$Origin', not '$ExpectedRemote'. It was not changed."
    }
}

$RepoProbe = Invoke-NativeProbe "gh" @("api", "repos/$Slug")
$RepoDisposition = Get-RepositoryProbeDisposition $RepoProbe
$RepoCreated = $false
if ($RepoDisposition -eq "Exists") {
    try { $Repo = $RepoProbe.Output | ConvertFrom-Json }
    catch { Stop-Safely "GitHub returned invalid repository metadata for $Slug." }
} else {
    $HttpStatus = Get-GitHubHttpStatus $RepoProbe.Output
    if ($RepoDisposition -eq "Unauthorized") {
        Stop-Safely "GitHub denied access while checking $Slug (HTTP $HttpStatus). Authentication or repository authorization must be corrected; the repository was not treated as absent."
    }
    if ($RepoDisposition -eq "Failure") {
        Stop-Safely "Unable to determine whether $Slug exists. gh exited $($RepoProbe.ExitCode): $($RepoProbe.Output)"
    }

    # Recheck identity immediately before creating. A 404 is accepted as
    # absence only for the expected authenticated owner.
    $OwnerRecheck = Invoke-NativeProbe "gh" @("api", "user", "--jq", ".login")
    if ($OwnerRecheck.ExitCode -ne 0 -or $OwnerRecheck.Output -cne $ExpectedOwner) {
        Stop-Safely "Repository lookup returned 404, but authenticated ownership could not be reconfirmed as $ExpectedOwner. No repository was created."
    }

    Write-Host "Repository $Slug does not exist for the verified owner; creating it as PRIVATE." -ForegroundColor Cyan
    $CreateProbe = Invoke-NativeProbe "gh" @("repo", "create", $Slug, "--private", "--description", "Reproducible PrimeKG repurposing benchmark migration and validation")
    if ($CreateProbe.ExitCode -ne 0) {
        Stop-Safely "Private repository creation failed. This can indicate insufficient authorization or an inaccessible existing repository; no remote was changed. gh output: $($CreateProbe.Output)"
    }
    $RepoCreated = $true
    $RepoProbe = Invoke-NativeProbe "gh" @("api", "repos/$Slug")
    if ($RepoProbe.ExitCode -ne 0) {
        Stop-Safely "Repository creation returned success, but $Slug could not be verified: $($RepoProbe.Output)"
    }
    try { $Repo = $RepoProbe.Output | ConvertFrom-Json }
    catch { Stop-Safely "GitHub returned invalid repository metadata after creating $Slug." }
}

if ($Repo.owner.login -cne $ExpectedOwner -or $Repo.full_name -cne $Slug) {
    Stop-Safely "Repository identity mismatch: expected $Slug, received '$($Repo.full_name)' owned by '$($Repo.owner.login)'."
}
if (-not $Repo.private) { Stop-Safely "Repository $Slug exists but is not private. Refusing to use it." }
if (-not $RepoCreated -and [int64]$Repo.size -gt 0 -and -not $Origin) {
        $Adopt = Read-Host "Private repository $Slug already contains data. Type the exact slug to confirm it is this project"
        if ($Adopt -cne $Slug) { Stop-Safely "Refusing to overwrite or adopt an unconfirmed existing repository." }
}

if ($Origin) {
    Write-Host "Using verified origin $Origin."
} else {
    Invoke-Native "git" @("remote", "add", "origin", "$ExpectedRemote.git")
}

$RemoteMain = (& git ls-remote --heads origin main | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { Stop-Safely "Unable to inspect remote main." }
if ($RemoteMain) {
    Invoke-Native "git" @("fetch", "origin", "main")
    & git merge-base --is-ancestor origin/main HEAD
    if ($LASTEXITCODE -ne 0) { Stop-Safely "Remote main is not an ancestor of local HEAD. Pull/reconcile manually; no push was attempted." }
}

Invoke-Native "git" @("push", "--set-upstream", "origin", "main")
Invoke-Native "git" @("push", "origin", "phase2-gate5", "phase2-gate6a")

$LocalHead = Capture-Native "git" @("rev-parse", "HEAD")
$RemoteHead = Capture-Native "gh" @("api", "repos/$Slug/commits/main", "--jq", ".sha")
$Private = Capture-Native "gh" @("api", "repos/$Slug", "--jq", ".private")
if ($LocalHead -ne $RemoteHead) { Stop-Safely "Push verification failed: local $LocalHead, remote $RemoteHead" }
if ($Private -ne "true") { Stop-Safely "Post-push privacy verification failed." }
if (git status --porcelain) { Stop-Safely "Publication completed, but the worktree is not clean. Review git status." }

Write-Host "SUCCESS" -ForegroundColor Green
Write-Host "Private repository: https://github.com/$Slug"
Write-Host "Verified main: $RemoteHead"
Write-Host "Verified tags: phase2-gate5, phase2-gate6a"
