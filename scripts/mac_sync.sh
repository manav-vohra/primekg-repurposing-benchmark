#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-}"
[[ "$ACTION" == "start" || "$ACTION" == "finish" ]] || { echo "Usage: bash scripts/mac_sync.sh start|finish" >&2; exit 2; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ -z "$(git status --porcelain)" ]] || { echo "Uncommitted changes detected; commit or stash them deliberately first." >&2; exit 1; }
BRANCH="$(git branch --show-current)"
[[ -n "$BRANCH" ]] || { echo "Detached HEAD is not supported." >&2; exit 1; }
git fetch --prune origin

if [[ "$ACTION" == "start" ]]; then
  git pull --ff-only origin "$BRANCH"
  echo "Ready to work on $BRANCH at $(git rev-parse --short HEAD)."
else
  git merge-base --is-ancestor "origin/$BRANCH" HEAD || { echo "Local and remote histories diverged or local is behind; reconcile without force-pushing." >&2; exit 1; }
  git push origin "$BRANCH"
  git push origin --follow-tags
  echo "Pushed $BRANCH safely at $(git rev-parse --short HEAD)."
fi
