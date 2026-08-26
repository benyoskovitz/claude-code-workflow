# Output styles, for rules about how every answer is written

An output style is appended to Claude Code's system prompt and applies to every response in the session. Use one when the thing you want to change is *how the agent talks to you*, in every answer, regardless of the task.

## Files

- `plain-english.md`: explain technical work to someone who is technical-adjacent but doesn't read code for a living. Define every name on first use, including the ones you invent yourself, say what the thing does rather than how you investigated it, and end with a decision they can act on without reading back up.

## Install

Copy the file into `~/.claude/output-styles/` (yours alone) or `.claude/output-styles/` (shared with the project), then set the style in a settings file:

```json
{
  "outputStyle": "Plain English"
}
```

In a terminal session you can pick it from a menu with `/config` instead, which writes the same key to `.claude/settings.local.json`. The standalone `/output-style` command was removed in v2.1.91.

The system prompt is read once when a session starts, so a change takes effect in the next session or after `/clear`.

## Why an output style and not a CLAUDE.md rule

This is the part worth understanding, because the obvious choice is the wrong one.

A CLAUDE.md rule is injected as a user message near the start of the session. It works fine for facts the agent needs to look up. It works badly for a rule that has to hold in *every* answer, because thirty tool calls into a technical task, that instruction is buried under diffs and file contents and nothing pulls the agent back to it. The register drifts toward whatever it's currently reading, which is code.

Output styles get automatic adherence reminders during the conversation. That single mechanism is the reason to prefer one here.

**Keep `keep-coding-instructions: true`** unless the agent genuinely isn't writing software. Without it, a custom style drops Claude Code's built-in engineering instructions covering how to scope changes, write comments, and verify work. With it, your instructions are added on top and nothing is lost.

## Two things to know before you write your own

**Style rules need pass conditions, same as any other instruction.** "Avoid jargon" is unenforceable and will drift. A table of specific terms with their plain replacements, an explicit always-cut and always-keep list, and a closing checklist are what actually hold. A draft made only of adjectives reads like a style guide and enforces nothing, because no line in it can ever come back false. Nothing that cannot fail can hold.

**A checklist you run on yourself is worth less than it looks, so put a hook behind the parts a machine can settle.** This file's em-dash ban needs no judgment and is repeated in three other places in the same context window. Measured over one user's real session history, 32% of replies still contained one. `../hooks/plain-english-gate.py` is a `Stop` hook that reads the finished reply and blocks the turn on an em dash in the agent's own prose, or on a coined label in any question in the closing region that appears nowhere else in the reply. Two items out of twelve. The rest still depend on the agent, and that 32% is roughly the going rate for those.

**Define the names you invent, not just the ones you borrowed.** The obvious version of "define every name" reaches file paths, config keys, function names: things that exist and can be looked up. It misses the phrase the agent coins mid-reply to compress an argument it just made ("the self-disarming problem"), which is worse, because there is nothing to look up at all. Those land in the closing question especially often, because squeezing an ask down to one line is exactly what makes a writer reach for a label. `Rule 3` therefore requires the closing question to make sense to someone who read nothing above it, even at the cost of running two or three sentences.

**Govern length by kind, not by a word count.** A style that only governs word choice produces answers that are simple and interminable, which is its own failure. But the obvious fix is the wrong one. An earlier version of `plain-english.md` carried a word budget, and a budget deletes the definitions first, because a definition is the part that feels redundant to the writer who already knows the term. `Rule 2` names the kinds of content to cut instead, and leaves everything on its keep list at whatever length it takes.

That was re-measured, not assumed. Across one user's full session history, the replies they rejected split almost exactly evenly around the length of a typical reply: 18 of 37 shorter, 19 longer. Length by itself does not predict a rejection. What they reject a reply over is usually a clause of about nine words buried inside, and a limit makes that clause more likely, not less, because compression is what produces it. The replies that genuinely were walls were mostly a sub-agent's report pasted through verbatim. So the instrument is ordering (the answer and the ask first, everything supporting them below) plus not pasting long verbatim blocks, and there is no number anywhere in the file.

## Limits

Output styles apply to the main conversation only. A sub-agent runs its own system prompt and won't inherit the style, so a skill that prints its own report verbatim comes back in the default register. If that matters to you, put a one-line pointer in CLAUDE.md as a fallback, since sub-agents do read that.

This is not a small leak. In the history behind this file, 93% of the replies that pasted a sub-agent's report verbatim carried an em dash, against 32% of the rest, and most of the replies the reader rejected as too long were that same paste. The hook skips text inside `<details>` and inside fenced code blocks, on the grounds that an audit record is not the main session's prose to rewrite. Do not assume that escape happens by itself: in the same history only 39% of those relays were fenced or wrapped, so the hook would have blocked 93% of them, and the workflow step that pastes them forbade editing a word. If a skill of yours pastes a sub-agent's report, make it require the fence. Better still, summarise the sub-agent instead of pasting it, and keep the verbatim block only when you actually need the record.

The hook has one more limit worth knowing before you install it: the reply is streamed to the reader **before** a `Stop` hook runs. It cannot suppress a bad reply. What it removes is the round trip, since the correction arrives immediately without the reader having to ask for it.
