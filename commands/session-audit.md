Self-audit pass over CLAUDE.md rules and memory files. Surfaces stale rules, undocumented workarounds, and contradictions between memory and current code. Read-only by default — never modifies CLAUDE.md or memory without explicit confirmation.

This pairs with `/session-end` (which it used to be part of) and with the workflow-meta lab: session-end is the deterministic wrap-up, session-audit keeps the ruleset honest on its own cadence.

**When to run:**
- After a long session where you referenced lots of CLAUDE.md rules
- When you've applied the same workaround repeatedly and want to capture it
- Before a major refactor (start with a clean ruleset)
- Periodically — once a week is a reasonable default

## 1. Scope the audit

Default (no args): everything you touched this session — CLAUDE.md rules you cited, memory files you read, patterns you applied repeatedly. With `--full`: the entire project + global CLAUDE.md and the whole memory directory.

## 2. Check for staleness

Review CLAUDE.md (project + global) and memory files. Flag if:

- A **CLAUDE.md rule is wrong or outdated** vs what you saw in code (it says "X lives in `path/foo`" but `foo` moved or is gone)
- A **workaround you applied 2+ times** isn't documented anywhere
- A **memory file contradicts** current code — the named file/symbol no longer exists, or behavior changed
- A **feedback memory was promoted** to CLAUDE.md and the memory entry is now redundant
- The **global and project CLAUDE.md have new overlap** — same rule in both, one should win
- A **CLAUDE.md rule duplicates a hook** that already enforces it — dead text
- A **memory file's description doesn't match its content**

## 3. Cross-check against recent commits

Run `git log --oneline --since="30 days ago"` and look for patterns the rules don't cover:

- Repeated commit subjects fixing the same class of bug → candidate for a new rule
- Reverts → an existing rule may be wrong
- Long forensic commit messages → candidate to distill into a memory or CLAUDE.md entry

## 4. Present findings

Group by severity. Don't propose fixes inline — just enumerate.

```
WRONG (must fix):
- CLAUDE.md line N: "<rule>" — but <observed contradiction> (see <file:line>)
- memory/<file>: references removed symbol <X> (see commit <sha>)

REDUNDANT (consider removing):
- memory/<file>: promoted to CLAUDE.md "<section>" on <date>

GAPS (consider adding):
- Workaround applied 3× this session: <pattern>. Not documented.
- Same pattern across recent PRs (#a, #b, #c). Could be a rule.
```

## 5. Confirm before changing

For each finding, ask: fix now / defer / dismiss. Only modify CLAUDE.md or memory after explicit per-item confirmation. Default is defer. If the user says "fix all wrong, dismiss the rest," do that — don't ask 12 separate questions.

## 6. Commit grouped changes

If any CLAUDE.md or memory changes were made, commit them in one focused commit (stage by name, not `git add .`), then push to the project's normal ref.

## What this does NOT do

- Does not modify code (only CLAUDE.md and memory files)
- Does not run tests, build, lint
- Does not commit session notes — that's `/session-end`
- Does not clean up worktrees — that's `/worktree-janitor`

Keep the scope tight. The point is to keep the ruleset honest, not to refactor the project.
