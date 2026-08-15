#!/usr/bin/env bash
# supply-chain-scan.sh — zero-dependency sweep for the npm whitespace-injector
# config RAT and unpinned npx installs. Pure grep/bash, no network, read-only.
# Usage: bash supply-chain-scan.sh [/path/to/repo]   (defaults to current dir)
# Exit:  0 = clean, 1 = findings.
set -uo pipefail

REPO="${1:-$(pwd)}"
findings=0

echo "supply-chain-scan: $REPO"
echo

# 1. CRITICAL — whitespace-injector signature: 200+ blank run before code in JS/TS.
#    The actual postcss.config RAT tell (payload pushed off-screen to the right).
while IFS= read -r f; do
  hit=$(grep -nE '[[:blank:]]{200,}[^[:blank:]]' "$REPO/$f" 2>/dev/null) || continue
  echo "  [CRITICAL] whitespace-injector signature — $f"
  printf '%s\n' "$hit" | head -2 | cut -c1-80 | sed 's/^/             /'
  findings=$((findings + 1))
done < <(git -C "$REPO" ls-files '*.js' '*.mjs' '*.cjs' '*.ts' '*.tsx' 2>/dev/null \
         | grep -vE '(^|/)node_modules/')

# 2. WARN — unpinned 'npx ...@latest' in package.json / MCP configs (re-resolves every run).
while IFS= read -r f; do
  hit=$(grep -nE 'npx[^"]*@latest' "$REPO/$f" 2>/dev/null) || continue
  echo "  [WARN] unpinned 'npx ...@latest' — $f"
  printf '%s\n' "$hit" | head -2 | sed 's/^/             /'
  findings=$((findings + 1))
done < <(git -C "$REPO" ls-files '*package.json' '*.mcp.json' 'mcp.json' '*claude_desktop_config.json' 2>/dev/null)

echo
if [ "$findings" -eq 0 ]; then
  echo "CLEAN — no injector signature or @latest npx in tracked files."
  exit 0
fi
echo "$findings finding(s). If CRITICAL: STOP — do not build/commit; clean the machine, rotate credentials."
exit 1
