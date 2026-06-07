# Hooks, guardrails that fire automatically

Hooks turn "rules I hope the agent remembers" into "reminders the system injects at the right moment." Three placements do most of the work:

- **PreToolUse**: inspect a tool call before it runs. Use it to catch a `git commit` and remind the agent to run `/pre-commit` first.
- **UserPromptSubmit**: inject a reminder on every turn. Use it for the one or two failure modes you keep hitting, so they're always in context.
- **PostToolUse**: react to an edit. Use it to nudge "you just touched a file that needs a smoke test / schema sync."

The *mechanism* here is fully reusable. The *contents* (which files trigger which reminder) are yours to fill in, they should encode your project's specific recurring drift, not mine.

## Files

- `settings.json`: the hook wiring. Copy into `.claude/settings.json` and edit the reminder text.
- `post-edit-trigger.sh`: example PostToolUse script: matches edited file paths against a trigger list and prints a reminder to stderr. Genericized from a real smoke-test trigger.

## Notes

- Hooks print to **stderr** and `exit 0`. They surface a reminder; they don't block. (A non-zero exit can block a tool call if you want a hard gate, use sparingly.)
- Keep the inline JSON hooks short. Anything with logic (path matching, grep) belongs in a `.sh` script the hook calls, like `post-edit-trigger.sh`.
- These pair with the `/pre-commit` skill: the PreToolUse hook reminds, the skill does the actual checking. Belt and suspenders.
