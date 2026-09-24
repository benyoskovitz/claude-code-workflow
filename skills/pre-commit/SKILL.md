---
name: pre-commit
description: >
  Pre-commit quality gate. Scans the staged diff for known anti-patterns and
  security issues, runs the test + type-check suite, and blocks on any BLOCK-level
  hit. Run before every commit. Reinforced by the PreToolUse hook in
  hooks/settings.json.
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob
---

# /pre-commit, quality gate before commit

Scan the staged diff for known anti-patterns before committing. This is the last
automated check before code ships. Unlike `/assess` (per-task rubric), this runs
the same global checks on every commit.

> This is a genericized scaffold. The check *categories* and the BLOCK/WARN model
> are the reusable part. Replace the specific patterns with the anti-patterns that
> actually bite in your stack, the most valuable ones are the mistakes you keep
> repeating.

## When to run

**ALWAYS before creating a git commit.** Not optional. If the user asks you to
commit, run this first.

## Steps

### 1. Get the staged diff

```bash
git diff --staged
```

If nothing is staged, fall back to `git diff HEAD`. If there are no changes,
report "Nothing to check" and stop. **Only check added lines** (the `+` lines).
Don't flag pre-existing code the change didn't touch.

### 2. Anti-pattern checks

Assign each finding a severity: **BLOCK** (must fix before commit) or **WARN**
(surface, let the user decide). A starter set, tune to your stack:

- **Hardcoded secrets**: strings shaped like API keys, tokens, or connection
  strings (`sk-`, `key-`, long alphanumerics, `postgres://...@...`). **BLOCK.**
- **Missing auth on new endpoints**: a new server action / route handler that
  doesn't call your auth helper. **BLOCK.**
- **Raw string interpolation into queries**: template literals inside query
  builders. Use parameterized queries. **BLOCK.**
- **Supply-chain config injection**: a config file (`postcss.config.*`,
  `next.config.*`, `tailwind.config.*`) with a run of 200+ spaces/tabs before
  code — the 2026 npm "whitespace-injector" RAT hides its payload off-screen to
  the right, invisible in editors and diffs. `grep -nE '[[:blank:]]{200,}[^[:blank:]]'`.
  **BLOCK** (stop, don't build, rotate any credential the build could read).
- **Unpinned `npx ...@latest`**: re-resolves to whatever's newest on every run —
  the supply-chain attack's entry point. Pin to an exact version. **WARN.**
- **Debug artifacts**: `console.log`, commented-out code blocks, `TODO: remove`.
  **WARN.**
- **Fire-and-forget async**: unawaited promises in serverless handlers (they
  silently never complete). **WARN.**
- **Generic error messages**: `"Something went wrong"` swallowing the real error.
  **WARN.** This matches literal strings, so it cannot see a message that is
  generic in other words, or whether the error reached anyone. It is a floor, not
  the rule. The rule, for your CLAUDE.md or a `rules/` file: every failure message
  names something the reader can do, and every caught error reaches either the
  reader or your error monitoring, with the diff showing which. Show the error's
  own text when the reader can act on it. When it is a framework artifact they
  can't act on, report it to monitoring and show the action alone.
- **<Your stack's recurring footguns>**: add the patterns you keep re-learning.

### 3. Tests and types

```bash
<your test command>      # e.g. npm run test:run, failing tests are BLOCK
<your typecheck command> # e.g. npx tsc --noEmit, type errors are BLOCK
```

Note passing results in the summary ("Tests: N passed", "Types: OK").

**Test-coverage nudge (WARN):** for each new or substantially changed logic file
in the diff, check whether a sibling test file exists. Exclude thin wrappers,
config, types, and UI-only files. This is a nudge, not a block.

### 4. Project-specific checks

Run any pre-commit checks the project declares for itself. Look for a section titled "Project-specific pre-commit checks" (or similar) in the project's `CLAUDE.md`, or for declarations under the project's `.claude/`. Run each command the project lists and apply its declared severity (BLOCK, WARN, or advisory). If the project declares none, skip this step silently.

These live in the project, not here, because the scripts and paths they name exist only in that repo. Hardcoding them in this skill makes it error or mislead everywhere else. Examples a project might declare: a docs-staleness script, a sitemap or structured-data check for its marketing site, or an integration-test suite that needs a local service.

### 5. Report

```
PRE-COMMIT CHECK
================

BLOCKED (must fix before committing):
  ✗ <finding> at <file:line>
    Fix: <what to do>

WARNINGS (review before committing):
  ⚠ <finding> at <file:line>

PASSED: N checks passed

Result: <BLOCKED, fix above | All checks passed, ready to commit>
```

## Behavior

- **BLOCK** → do not proceed with the commit; the user must fix.
- **WARN** → show them; ask whether to proceed or fix first.
- **All clear** → proceed silently (just "All checks passed").
- **Be practical, not pedantic.** If a pattern is obviously intentional (a test
  file exercising `confirm()`), don't flag it.
- **Keep it fast.** This runs on every commit. Don't read files unless a diff
  finding points you at one.
