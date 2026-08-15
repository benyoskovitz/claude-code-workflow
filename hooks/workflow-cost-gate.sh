#!/bin/bash
# workflow-cost-gate.sh
# PreToolUse hook for the Workflow tool.
#
# Forces a cost warning and an explicit confirmation before ANY dynamic workflow
# runs. A workflow can silently fan out hundreds of sub-agents and burn millions
# of tokens. In one real incident, an instruction-audit workflow spawned 495
# agents and consumed 4.1M output tokens, exhausting the session quota and
# costing real money, for findings a single solo pass produced at one to two
# orders of magnitude less cost.
#
# Emits permissionDecision "ask" so the user always sees a confirm prompt with
# the reason. Fails open (exit 0, no decision) only if it cannot read the input.
#
# Requires: jq

input=$(cat)

# Workflow input is one of: inline `script`, a `scriptPath` file, or a named workflow.
script=$(printf '%s' "$input" | jq -r '.tool_input.script // ""' 2>/dev/null)
scriptPath=$(printf '%s' "$input" | jq -r '.tool_input.scriptPath // ""' 2>/dev/null)
name=$(printf '%s' "$input" | jq -r '.tool_input.name // ""' 2>/dev/null)

src="$script"
if [ -z "$src" ] && [ -n "$scriptPath" ] && [ -f "$scriptPath" ]; then
  src=$(cat "$scriptPath" 2>/dev/null)
fi

# Heuristic fan-out signals (over-counts on purpose — better to over-warn).
agents=$(printf '%s' "$src" | grep -oE 'agent\(' | wc -l | tr -d ' ')
fans=$(printf '%s'   "$src" | grep -oE '(parallel|pipeline)\(' | wc -l | tr -d ' ')
loops=$(printf '%s'  "$src" | grep -cE '\b(while|for)\b' | tr -d ' ')

if [ -n "$name" ] && [ -z "$src" ]; then
  detail="named workflow \"$name\" (source not inlined — assume it may fan out widely)"
else
  detail="${agents} agent() call-sites, ${fans} parallel/pipeline fan-out(s), ${loops} loop(s)"
fi

risk="MODERATE"
if [ "${loops:-0}" -gt 0 ] || [ "${fans:-0}" -gt 2 ]; then risk="HIGH (loops or multi-stage fan-out present — agent count can multiply)"; fi

reason="⚠️ DYNAMIC WORKFLOW COST CHECK — confirm before this runs.
Workflows can spawn hundreds of sub-agents and burn millions of tokens.
Known incident: 495 agents / 4.1M output tokens / session quota exhausted (real \$ spent) for an instruction audit a solo pass did at 1-2 orders of magnitude less cost.
This script: ${detail}. Fan-out risk: ${risk}.
Before approving, Claude MUST state: (1) the MAXIMUM sub-agent count this can spawn, and (2) a rough token estimate. If fan-out is unbounded (loops over args/budget), state the hard cap instead. Do not proceed on a vague 'it'll fan out a bit'."

printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":%s}}\n' "$(printf '%s' "$reason" | jq -Rs .)"
exit 0
