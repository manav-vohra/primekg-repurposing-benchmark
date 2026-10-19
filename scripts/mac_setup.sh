#!/usr/bin/env bash
set -euo pipefail

REPO_SLUG="${PRIMEKG_REPO_SLUG:-manav-vohra/primekg-repurposing-benchmark}"
TARGET_DIR="${PRIMEKG_PROJECT_DIR:-$HOME/Projects/primekg-repurposing-benchmark}"

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "$1 is required."; }

need git
need python3

SCRIPT_PATH="${BASH_SOURCE[0]:-}"
if [[ -n "$SCRIPT_PATH" && -f "$SCRIPT_PATH" ]]; then
  CANDIDATE_ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
else
  CANDIDATE_ROOT=""
fi

if [[ -n "$CANDIDATE_ROOT" && -d "$CANDIDATE_ROOT/.git" ]]; then
  PROJECT_ROOT="$CANDIDATE_ROOT"
elif [[ -d "$TARGET_DIR/.git" ]]; then
  PROJECT_ROOT="$TARGET_DIR"
elif [[ -e "$TARGET_DIR" ]]; then
  die "$TARGET_DIR exists but is not a Git checkout; it was not modified."
else
  need gh
  gh auth status --hostname github.com >/dev/null 2>&1 || die "Authenticate first with: gh auth login --hostname github.com --web"
  mkdir -p "$(dirname "$TARGET_DIR")"
  gh repo clone "$REPO_SLUG" "$TARGET_DIR"
  PROJECT_ROOT="$TARGET_DIR"
fi

cd "$PROJECT_ROOT"
[[ -z "$(git status --porcelain)" ]] || die "Checkout has uncommitted changes; commit or stash them deliberately before setup."
[[ "$(git branch --show-current)" == "main" ]] || die "Expected branch main."
git fetch --prune origin
git pull --ff-only origin main

PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' || die "Python 3.10 or newer is required; found $PYTHON_VERSION."

if [[ "$(uname -m)" == "arm64" ]]; then
  printf 'Apple Silicon detected; pip will select native macOS/arm64 wheels. CUDA is neither required nor assumed.\n'
fi

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e '.[reconstruct,evaluator,e2,e3]' pytest

primekg-repurpose validate --tier reference --data-root artifacts/frozen
python -m pytest -q \
  tests/test_provenance.py \
  tests/test_benchmark_semantics.py \
  tests/test_evaluation.py \
  --basetemp work/pytest-macos-smoke

EXPECTED_FILES=(
  artifacts/recovered/external/p1_e3_complex_base_nonther_triples.npz
  artifacts/recovered/external/p1_e3_complex_clean_indication_triples.npz
  artifacts/recovered/external/p1_e3_complex_seed0_base_pretrain.pt
  artifacts/recovered/external/p1_e3_complex_seed1_base_pretrain.pt
  artifacts/recovered/external/p1_e3_complex_seed2_base_pretrain.pt
)
printf '\nExternal scientific objects intentionally absent unless separately transferred and hash-verified:\n'
for path in "${EXPECTED_FILES[@]}"; do
  [[ -f "$path" ]] || printf '  - %s\n' "$path"
done
printf '  - raw PrimeKG kg.csv\n  - historical E3/E4 score archives\n'

printf '\nSUCCESS\nProject: %s\nCommit: %s\nPython: %s\n' "$PROJECT_ROOT" "$(git rev-parse HEAD)" "$(python --version 2>&1)"
printf 'Start work safely with: bash scripts/mac_sync.sh start\n'
