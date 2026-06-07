# Path-scoped rules

The problem: CLAUDE.md loads on every session, and a big one reduces adherence (Anthropic's soft target is under 200 lines). But you have hard-won, stack-specific tactical knowledge you don't want to lose.

The fix: move that tactical content out of CLAUDE.md into topical files here, each with `paths:` frontmatter. A rule with `paths:` loads **only when the agent reads a file matching one of its globs**. So on a docs-only or non-stack session, none of it loads — but the moment the agent opens a matching source file, the relevant rule lazy-loads in full.

## The litmus test

For every line of guidance, ask:

> Does this shape how the agent *thinks*, or just tell it what to *do*?

- **How it thinks** (behavioral principles, security posture, your workflow loop, architectural non-negotiables) → stays in CLAUDE.md, loads unconditionally.
- **What it does** (framework-specific patterns, tactical footguns, file-type conventions) → moves here with a `paths:` glob.

## Rules that bit me (so you don't repeat them)

1. **YAML frontmatter MUST be on line 1.** If anything — even a comment — precedes the opening `---`, the parser silently ignores `paths:` and the rule loads unconditionally. Comments go *after* the closing `---`.
2. **Split by topic, not into one big file.** Different content needs different globs (UI patterns want component paths; SEO rules want marketing-page paths). One mega-file defeats the scoping.
3. **User scope vs project scope.** Put cross-project stack rules in `~/.claude/rules/` so every project shares them without copies. Put genuinely project-specific rules in `./.claude/rules/`.
4. **Default the globs broad, then tighten.** Too narrow and the rule under-fires; too broad and you re-pollute context. Start broad, narrow if you observe noise.

See `example-stack-rule.md` for the shape.
