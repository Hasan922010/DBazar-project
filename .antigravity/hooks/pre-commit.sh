#!/usr/bin/env bash
# DBazar Pre-Commit Security & Contract Audit Hook (`.antigravity/hooks/pre-commit.sh`)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[DBazar Pre-Commit] Running Contract-First & B2B Security Audit..."
./run.sh test
