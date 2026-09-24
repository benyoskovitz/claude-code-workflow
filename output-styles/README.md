# Output styles, for rules about how every answer is written

An output style is appended to Claude Code's system prompt and applies to every response in the session. Use one when the thing you want to change is *how the agent talks to you*, in every answer, regardless of the task.

## Files

- `plain-english.md`: explain technical work to someone who ships product but doesn't read code for a living. The answer comes first, nothing is shorthand, every skipped check is named, the length fits the question, and the agent asks only when it needs a decision.

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

## Why the style is short

An earlier version of this file ran to about 300 lines: four numbered rules, a structure section, a translation table for jargon, a "never" list and a closing self-check. It was followed worse than the current version, which is under 70 lines, for three reasons that showed up in real replies.

- **A long rulebook gets skimmed.** The replies that broke the style broke rules it already stated plainly. About a third of one reply was confession, which the file banned. Another closed on shorthand the reader had never seen, which the file also banned. More rules did not mean more of them held.
- **Obeying it made replies longer.** The file required an explanation, the cost, what was not done, and a closing question on every reply. A reply that did all four was long by construction, whatever the question was. The current file ties length to the question and asks only when a decision is needed.
- **Its own hook made the agent say everything twice.** The Stop hook blocked any em dash and told the agent to say the reply again, corrected. So a single dash inside a quoted product string produced a duplicate reply. The reader did not mind the dash. The hook now checks one thing, and asks for the corrected question only (see `../hooks/README.md`).

The rules that survived are the ones that cut: answer first, no shorthand, name what you skipped, no narration or confession, a sentence-length ceiling. Before you add a rule back, check it against those three reasons.

## Three things to know before you write your own

**Style rules need pass conditions, same as any other instruction.** "Avoid jargon" is unenforceable and will drift. "No sentence over twenty-five words" and "the first line is the answer" can each come back false, so each can hold. A rule that cannot fail cannot hold.

**Treat an invented name as shorthand, the same as a borrowed one.** The obvious version of "define every name" reaches file paths, config keys, function names: things that exist and can be looked up. It misses the phrase the agent coins mid-reply to compress an argument it just made ("the self-disarming problem"), which is worse, because there is nothing to look up at all. Those land in the closing question especially often, because squeezing an ask down to one line is exactly what makes a writer reach for a label. That is why the file says a label you invented is shorthand, and why the one check in `../hooks/plain-english-gate.py` looks for exactly that.

**Govern length by the question, not by a word count.** A word budget deletes the definitions first, because a definition is the part that feels redundant to the writer who already knows the term. Measured across one reader's session history, the replies they rejected split almost exactly evenly around the length of a typical reply. Length alone did not predict a rejection. What did was a clause of about nine words buried inside, and compression is what produces that clause. So the file matches length to the question and lets plain context take whatever room it needs.

## Limits

Output styles apply to the main conversation only. A sub-agent runs its own system prompt and won't inherit the style, so a skill that prints its own report verbatim comes back in the default register. If that matters to you, put a one-line pointer in CLAUDE.md as a fallback, since sub-agents do read that.

Most of the replies that same reader rejected as too long were a sub-agent's report pasted through verbatim. Summarise a sub-agent instead of pasting it, and keep the verbatim block only when you need the record, as `/assess` does for its grade.
