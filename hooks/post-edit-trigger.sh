#!/usr/bin/env bash
# Example PostToolUse hook. Matches the edited file path against a trigger list
# and prints a reminder to stderr. Genericized from a real smoke-test trigger.
#
# Pattern: when the agent edits a file that has downstream verification needs
# (a smoke test, a schema-sync check, a regenerate step), nudge it to run that
# step before committing. Replace the cases below with your own triggers.

set -euo pipefail

input=$(cat)
file_path=$(echo "$input" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("file_path",""))' 2>/dev/null)

[ -z "$file_path" ] && exit 0
[ -f "$file_path" ] || exit 0

case "$file_path" in
  # Example: edits under a pipeline/LLM directory should trigger a smoke test —
  # but only if the file actually makes an external call (cheap grep gate).
  *<YOUR_LLM_DIR>*)
    grep -qE '<YOUR_EXTERNAL_CALL_HELPERS>' "$file_path" || exit 0
    echo "REMINDER: edited $file_path — run <YOUR_SMOKE_COMMAND> before committing." >&2
    ;;

  # Example: edits to a schema source of truth should trigger a sync check.
  *<YOUR_SCHEMA_FILE>*)
    echo "REMINDER: edited $file_path — run the schema-sync check before committing." >&2
    ;;

  *)
    exit 0
    ;;
esac

exit 0
