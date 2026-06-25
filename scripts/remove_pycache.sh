#!/usr/bin/env bash
# remove_pycache.sh — untrack __pycache__ dirs and compiled Python files
#
# The .gitignore already lists __pycache__/ and *.pyc, but those paths were
# committed before the rule existed so Git still tracks them (issue #15).
#
# This script untracks them WITHOUT deleting files from disk, then prints
# a reminder to commit the result.
#
# Usage (run from the repo root):
#   bash scripts/remove_pycache.sh

set -euo pipefail

echo "==> Untracking __pycache__ directories and compiled bytecode files..."

# Untrack all __pycache__ directories
git ls-files --ignored --exclude-standard -z -d | \
    grep -z '__pycache__' | \
    xargs -0 --no-run-if-empty git rm -r --cached --quiet

# Untrack any .pyc / .pyo / .pyd files that slipped through
git ls-files '*.pyc' '*.pyo' '*.pyd' -z | \
    xargs -0 --no-run-if-empty git rm --cached --quiet

echo ""
echo "Done.  Git will no longer track these files."
echo "Now run:"
echo "  git commit -m 'chore: untrack __pycache__ and compiled bytecode'"
echo "  git push"
