# Hooks, guardrails that fire automatically

Hooks turn "rules I hope the agent remembers" into "reminders the system injects at the right moment." Four placements do most of the work:

- **SessionStart**: put something in context before the first prompt. Use it to read the open items from the last two session-notes files back in, so a new session starts knowing where the previous one stopped.
- **PreToolUse**: inspect a tool call before it runs. Use it to catch a `git commit` and remind the agent to run `/pre-commit` first.
- **UserPromptSubmit**: inject a reminder on every turn. Use it for the one or two failure modes you keep hitting, so they're always in context.
- **PostToolUse**: react to an edit. Use it to nudge "you just touched a file that needs a smoke test / schema sync."
- **Stop**: inspect the finished reply. Use it for rules about how the agent *writes*, which are the ones a self-check is worst at.

`SessionStart` and `UserPromptSubmit` are the two whose stdout Claude actually reads. For every other placement, stdout goes to the debug log and only **stderr** reaches the agent.

The *mechanism* here is fully reusable. The *contents* (which files trigger which reminder) are yours to fill in, they should encode your project's specific recurring drift, not mine.

## Files

- `settings.json`: the hook wiring, plus one `env` setting that compacts long sessions earlier. Copy into `.claude/settings.json` and edit the reminder text.
- `session-start-notes.sh`: SessionStart reader. Prints only the `Next Steps` and `Blockers / Open Questions` sections of the last two session notes.
- `post-edit-trigger.sh`: example PostToolUse script: matches edited file paths against a trigger list and prints a reminder to stderr. Genericized from a real smoke-test trigger.
- `workflow-cost-gate.sh`: PreToolUse gate on the `Workflow` tool. Forces a confirmation prompt with a fan-out estimate before any dynamic workflow runs. Needs `jq`.
- `plain-english-gate.py`: Stop hook that reads the finished reply and blocks on the one writing rule a machine can settle well: an invented label in the closing question. Pairs with `../output-styles/plain-english.md`. No dependencies.

## Compact earlier

This is one line of config, and it is probably the biggest token saving in this repo.

Every call re-sends the whole conversation so far, so a turn's cost grows with the size of the session. Claude Code compacts (summarises the conversation so far and carries on from the summary) when the session nears its window. On a 1M-token window that almost never happens, so long sessions keep paying for their whole history on every turn. In one measured history, about nine in ten input tokens were read on turns that already carried more than 150K tokens of history.

`settings.json` sets the window compaction plans around:

```json
"env": { "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "300000" }
```

It accepts 100K to 1M tokens, and it overrides both the `autoCompactWindow` setting and the `/autocompact` command. Compaction fires a little below it, to leave room for the summary. Modelled on that same history, 300K roughly halves the tokens read. Lower values save more but compact two to three times as often, and every summary is a chance to lose a detail. Start at 300K, measure, then decide.

Two costs to know. `/autocompact` can no longer raise the window for one long session; remove the line for that session instead. And resuming an old session that is already past the window compacts it at once, which costs one summary.

Check it took effect in a fresh process:

```bash
claude -p "/autocompact"
```

A pass prints `Auto-compact window: 300k tokens (from CLAUDE_CODE_AUTO_COMPACT_WINDOW)`.

## The session-notes reader

`session-start-notes.sh` is the read half of `/session-end`, which writes one notes file per session into `session-notes/`. It prints only two sections from the last two files: `Next Steps` and `Blockers / Open Questions`. Everything it prints is re-sent on every turn of the new session, and in every sub-agent that session starts. The other sections describe work already done, and with parallel sessions that is usually another session's work. Printing the open items alone cut this hook's output to about a third.

## The writing gate

`plain-english.md` is a rule in loaded context, and a rule in loaded context does not hold on its own. So the one rule a machine can check with good precision gets a hook: an invented label in the closing question. It blocks when a hyphen-compound noun phrase ("the self-disarming problem") sits in the closing question and appears nowhere else in the reply, which is what a phrase the agent coined looks like from outside. It works because Claude Code hands `Stop` the finished text as `last_assistant_message`, so nothing has to parse a transcript.

When it blocks, it asks for the corrected question only. It does not ask for the reply again.

An earlier version also blocked on any em dash. The measured case for it was strong: in one user's history, about a third of replies broke the em-dash ban, although the ban was stated several times in context. It was still removed. The reader did not mind a dash in a reply to them, and the block told the agent to "say it again, corrected", so every hit sent the whole reply twice. A check that is precise but guards something nobody minds costs more than it saves. Put em-dash bans where the text reaches customers, not in replies to you.

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

Then prove it can fail before you trust a quiet run. From a clone of this repo:

```bash
python3 hooks/plain-english-gate.py --selftest
```

A pass prints `SELFTEST PASSED`. It reintroduces four violations, including two real ones taken from transcripts at their real length, and asserts a block on each. It then asserts *no* block on four passages that must pass, including a coined label that defines itself in place and two names taken from the user's own installed skills. Every one of those passages is a reply the style file actually accepts, which is a rule worth keeping if you add one: a fixture list is a second statement of the rules, and one that contradicts them is worse than no fixture at all. For the two skill-name passages it goes further and empties the installed-name set to prove those fire without it, because "it stayed quiet" is consistent with the exclusion working and equally consistent with the regex never matching. A check observed to be silent has proven nothing.

It also prints what it does **not** catch. Three real violations of the style file sit in a `known_misses` list the self-test asserts stay uncaught and names in its output. Recording a gap as a gap is a limit; filing the same gap under "correct passages left alone" states the rule a second time and contradicts the first.

### What it does not catch

It fires at most once per turn, so it never verifies the correction. Text inside `<details>` or a fenced code block is skipped on purpose, since a sub-agent's report pasted as an audit record is not the main session's prose to rewrite. It finds hyphen-compounds only: "the org-context feature" is caught, "the pending question" is not, because a pattern wide enough for the second fires on every ordinary noun phrase and a check that cries wolf gets ignored. The head nouns it looks in front of are a closed list too: "the frozen-window problem" is caught and "the frozen-window handoff" was not, until `handoff` was added. And it ignores replies under 100 words of prose, because its premise is that an argument got compressed into a label and a one-sentence reply has none. On one user's real transcripts it fired rarely, and most fires were right by hand-reading. And it cannot see the case the style file cares about most, a coined name defined once far above and then used bare in the closing question.

And the big one: **the reply is streamed to the reader before `Stop` runs.** This cannot suppress a bad reply. It forces the corrected question to arrive immediately and unprompted, which removes the round trip, not the reader seeing the sentence once.

## The cost gate

This is the one hook here that blocks rather than nudges, and it's worth explaining why.

A dynamic workflow can fan out into hundreds of sub-agents from a script you skimmed. In one real incident an instruction-audit workflow spawned 495 agents and burned 4.1M output tokens, exhausting a session's quota and costing real money, for findings a single ordinary pass produced at a fraction of the cost.

The hook reads the workflow script before it runs, counts `agent()` call sites and `parallel`/`pipeline` fan-outs, flags loops (which multiply everything), and returns `permissionDecision: "ask"` so you always get a confirm prompt with those numbers attached. It deliberately over-counts. Over-warning is cheap; the failure it prevents is not.

It's a floor, not a substitute for judgment. The prompt tells the agent to state a maximum sub-agent count and a token estimate before you approve. Don't wave that through.

### When a workflow is worth it

Workflows are an opt-in power tool, not a default mode.

- **Leave `ultracode` off.** That setting lets the agent decide on its own when a task earns a fan-out. That's a standing grant of autonomy, and it's the opposite of gating spend.
- **Invoke a workflow explicitly, per task**, and only where breadth genuinely beats a single context: a broad review or audit across many dimensions at once; a codebase-wide migration or sweep, one isolated worktree agent per site; a design decision worth several independent approaches judged against each other; or exhaustive research that needs multi-modal source fan-out.
- **Routine coding stays solo.** A workflow is not a faster way to write a feature.
- **The normal gate still applies to whatever a workflow produces.** Rubric, then `/assess`, then `/pre-commit`, then a human. A workflow proposes; it doesn't bypass review.

### Known limitation: it under-counts nested fan-out

The estimate comes from reading the top-level script. It cannot see what a spawned agent goes on to spawn. Since Claude Code v2.1.172 a sub-agent can spawn its own sub-agents up to five levels deep, so a script showing three `agent()` calls can still fan out far past what the prompt reports. The count is a floor on the real number, not a ceiling.

Two things follow. Read the numbers in the prompt as "at least this many," not "this many." And when a workflow's agents are themselves told to delegate, treat the estimate as unreliable and ask for the depth, not just the count.

Fixing this properly means parsing what each spawned agent is instructed to do, which the hook can't do from a script alone. Until then it's a documented gap rather than a solved one.

## Notes

- Hooks print to **stderr** and `exit 0`. They surface a reminder; they don't block. (A non-zero exit can block a tool call if you want a hard gate, use sparingly.) `plain-english-gate.py` is the exception here: it exits 2 on purpose, which is how a `Stop` hook sends its stderr back to the agent as an instruction.
- Keep the inline JSON hooks short. Anything with logic (path matching, grep) belongs in a `.sh` script the hook calls, like `post-edit-trigger.sh`.
- These pair with the `/pre-commit` skill: the PreToolUse hook reminds, the skill does the actual checking. Belt and suspenders.
- The SessionStart reader is the other half of `/session-end`. Without it the notes are write-only.
