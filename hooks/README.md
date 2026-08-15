# Hooks, guardrails that fire automatically

Hooks turn "rules I hope the agent remembers" into "reminders the system injects at the right moment." Four placements do most of the work:

- **SessionStart**: put something in context before the first prompt. Use it to read the last few session-notes files back in, so a new session starts knowing where the previous one stopped.
- **PreToolUse**: inspect a tool call before it runs. Use it to catch a `git commit` and remind the agent to run `/pre-commit` first.
- **UserPromptSubmit**: inject a reminder on every turn. Use it for the one or two failure modes you keep hitting, so they're always in context.
- **PostToolUse**: react to an edit. Use it to nudge "you just touched a file that needs a smoke test / schema sync."

`SessionStart` and `UserPromptSubmit` are the two whose stdout Claude actually reads. For every other placement, stdout goes to the debug log and only **stderr** reaches the agent.

The *mechanism* here is fully reusable. The *contents* (which files trigger which reminder) are yours to fill in, they should encode your project's specific recurring drift, not mine.

## Files

- `settings.json`: the hook wiring. Copy into `.claude/settings.json` and edit the reminder text.
- `post-edit-trigger.sh`: example PostToolUse script: matches edited file paths against a trigger list and prints a reminder to stderr. Genericized from a real smoke-test trigger.
- `workflow-cost-gate.sh`: PreToolUse gate on the `Workflow` tool. Forces a confirmation prompt with a fan-out estimate before any dynamic workflow runs. Needs `jq`.

## The cost gate

This is the one hook here that blocks rather than nudges, and it's worth explaining why.

A dynamic workflow can fan out into hundreds of sub-agents from a script you skimmed. In one real incident an instruction-audit workflow spawned 495 agents and burned 4.1M output tokens, exhausting a session's quota and costing real money, for findings a single ordinary pass produced at a fraction of the cost.

The hook reads the workflow script before it runs, counts `agent()` call sites and `parallel`/`pipeline` fan-outs, flags loops (which multiply everything), and returns `permissionDecision: "ask"` so you always get a confirm prompt with those numbers attached. It deliberately over-counts. Over-warning is cheap; the failure it prevents is not.

It's a floor, not a substitute for judgment. The prompt tells the agent to state a maximum sub-agent count and a token estimate before you approve. Don't wave that through.

### Known limitation: it under-counts nested fan-out

The estimate comes from reading the top-level script. It cannot see what a spawned agent goes on to spawn. Since Claude Code v2.1.172 a sub-agent can spawn its own sub-agents up to five levels deep, so a script showing three `agent()` calls can still fan out far past what the prompt reports. The count is a floor on the real number, not a ceiling.

Two things follow. Read the numbers in the prompt as "at least this many," not "this many." And when a workflow's agents are themselves told to delegate, treat the estimate as unreliable and ask for the depth, not just the count.

Fixing this properly means parsing what each spawned agent is instructed to do, which the hook can't do from a script alone. Until then it's a documented gap rather than a solved one.

## Notes

- Hooks print to **stderr** and `exit 0`. They surface a reminder; they don't block. (A non-zero exit can block a tool call if you want a hard gate, use sparingly.)
- Keep the inline JSON hooks short. Anything with logic (path matching, grep) belongs in a `.sh` script the hook calls, like `post-edit-trigger.sh`.
- These pair with the `/pre-commit` skill: the PreToolUse hook reminds, the skill does the actual checking. Belt and suspenders.
- The SessionStart reader is the other half of `/session-end`. That command writes one notes file per session into `session-notes/`; this hook reads the most recent three back. Without the hook the notes are write-only.
