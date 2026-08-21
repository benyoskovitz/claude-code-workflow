# Output styles, for rules about how every answer is written

An output style is appended to Claude Code's system prompt and applies to every response in the session. Use one when the thing you want to change is *how the agent talks to you*, in every answer, regardless of the task.

## Files

- `plain-english.md`: explain technical work to someone who is technical-adjacent but doesn't read code for a living. Define every name on first use, say what the thing does rather than how you investigated it, end with the decision.

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

**Style rules need pass conditions, same as any other instruction.** "Avoid jargon" is unenforceable and will drift. A table of specific terms with their plain replacements, an explicit always-cut and always-keep list, and a closing checklist are what actually hold. The first version of `plain-english.md` was all adjectives and it failed within a week.

**Govern length by kind, not by a word count.** A style that only governs word choice produces answers that are simple and interminable, which is its own failure. But the obvious fix is the wrong one. An earlier version of `plain-english.md` carried a word budget, and a budget deletes the definitions first, because a definition is the part that feels redundant to the writer who already knows the term. `Rule 2` names the kinds of content to cut instead, and leaves everything on its keep list at whatever length it takes.

## Limits

Output styles apply to the main conversation only. A sub-agent runs its own system prompt and won't inherit the style, so a skill that prints its own report verbatim comes back in the default register. If that matters to you, put a one-line pointer in CLAUDE.md as a fallback, since sub-agents do read that.
