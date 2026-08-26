# Hooks, guardrails that fire automatically

Hooks turn "rules I hope the agent remembers" into "reminders the system injects at the right moment." Four placements do most of the work:

- **SessionStart**: put something in context before the first prompt. Use it to read the last few session-notes files back in, so a new session starts knowing where the previous one stopped.
- **PreToolUse**: inspect a tool call before it runs. Use it to catch a `git commit` and remind the agent to run `/pre-commit` first.
- **UserPromptSubmit**: inject a reminder on every turn. Use it for the one or two failure modes you keep hitting, so they're always in context.
- **PostToolUse**: react to an edit. Use it to nudge "you just touched a file that needs a smoke test / schema sync."
- **Stop**: inspect the finished reply. Use it for rules about how the agent *writes*, which are the ones a self-check is worst at.

`SessionStart` and `UserPromptSubmit` are the two whose stdout Claude actually reads. For every other placement, stdout goes to the debug log and only **stderr** reaches the agent.

The *mechanism* here is fully reusable. The *contents* (which files trigger which reminder) are yours to fill in, they should encode your project's specific recurring drift, not mine.

## Files

- `settings.json`: the hook wiring. Copy into `.claude/settings.json` and edit the reminder text.
- `post-edit-trigger.sh`: example PostToolUse script: matches edited file paths against a trigger list and prints a reminder to stderr. Genericized from a real smoke-test trigger.
- `workflow-cost-gate.sh`: PreToolUse gate on the `Workflow` tool. Forces a confirmation prompt with a fan-out estimate before any dynamic workflow runs. Needs `jq`.
- `plain-english-gate.py`: Stop hook that reads the finished reply and blocks on two writing rules a machine can settle. Pairs with `../output-styles/plain-english.md`. No dependencies.

## The writing gate

The case for this one is a number. `plain-english.md` ends with a checklist the agent is supposed to run on its own draft. Its em-dash ban needs no judgment, is repeated in three other places in the same context window, and a regular expression settles it. Measured over 427 real replies from one user's session history: **32% still contained an em dash.** That is what a self-check is worth on a rule with no ambiguity in it at all.

So two items on that checklist get a hook instead. It blocks when it finds an em dash in the agent's own prose, or a hyphen-compound label in the closing question that appears nowhere else in the reply, which is what a phrase the agent invented looks like from outside. It works because Claude Code hands `Stop` the finished text as `last_assistant_message`, so nothing has to parse a transcript.

Register it in `.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      { "hooks": [ { "type": "command", "command": "python3 .claude/hooks/plain-english-gate.py" } ] }
    ]
  }
}
```

Then prove it can fail before you trust a quiet run:

```bash
python3 hooks/plain-english-gate.py --selftest
```

That reintroduces five violations, including two real ones taken from transcripts at their real length, and asserts a block on each. It then asserts *no* block on seven passages that must pass: an em dash inside fenced code, one inside a blockquote, one inside a `<details>` relay, a coined label that defines itself in place, and two names taken from the user's own installed skills. Every one of those passages is a reply the style file actually accepts, which is a rule worth keeping if you add one: a fixture list is a second statement of the rules, and one that contradicts them is worse than no fixture at all. For the two skill-name passages it goes further and empties the installed-name set to prove those fire without it, because "it stayed quiet" is consistent with the exclusion working and equally consistent with the regex never matching. A check observed to be silent has proven nothing.

It also prints what it does **not** catch. Three real violations of the style file sit in a `known_misses` list the self-test asserts stay uncaught and names in its output. Recording a gap as a gap is a limit; filing the same gap under "correct passages left alone", which an earlier draft of this hook did, states the rule a second time and contradicts the first.

### What it does not catch

It fires at most once per turn, so it never verifies the correction. Text inside `<details>` is skipped on purpose, since a sub-agent's report pasted as an audit record is not the main session's prose to rewrite, and in the measured history 93% of those relays carry an em dash. The coined-label check finds hyphen-compounds only: "the org-context feature" is caught, "the pending question" is not, because a pattern wide enough for the second fires on every ordinary noun phrase and a check that cries wolf gets ignored. The head nouns it looks in front of are a closed list too, which is a real limit and not a hidden one: "the frozen-window problem" is caught and "the frozen-window handoff" was not, until `handoff` was added. And it ignores replies under 100 words of prose, because its premise is that an argument got compressed into a label and a one-sentence reply has none: without that floor it flagged "the read-only check" and "the single-source rule" as invented names. Measured fire rate on real transcripts is about 1 reply in 70, at roughly 80% precision by hand-reading. And it cannot see the case the style file cares about most, a coined name defined once far above and then used bare in the closing question.

And the big one: **the reply is streamed to the reader before `Stop` runs.** This cannot suppress a bad reply. It forces the correction to arrive immediately and unprompted, which removes the round trip, not the reader seeing the sentence once.

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

- Hooks print to **stderr** and `exit 0`. They surface a reminder; they don't block. (A non-zero exit can block a tool call if you want a hard gate, use sparingly.) `plain-english-gate.py` is the exception here: it exits 2 on purpose, which is how a `Stop` hook sends its stderr back to the agent as an instruction.
- Keep the inline JSON hooks short. Anything with logic (path matching, grep) belongs in a `.sh` script the hook calls, like `post-edit-trigger.sh`.
- These pair with the `/pre-commit` skill: the PreToolUse hook reminds, the skill does the actual checking. Belt and suspenders.
- The SessionStart reader is the other half of `/session-end`. That command writes one notes file per session into `session-notes/`; this hook reads the most recent three back. Without the hook the notes are write-only.
