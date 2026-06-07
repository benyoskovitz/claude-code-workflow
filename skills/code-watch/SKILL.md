---
name: code-watch
description: >
  Run a two-lens audit on the current change — security/bugs in one pass, and
  conformance to the project's own quality rules in another. Use on demand after a
  non-trivial change that touches sensitive surfaces (auth, database queries, user
  input, file uploads, encryption) or when you want a deeper read than /pre-commit.
  Reads the diff and the project's CLAUDE.md directly; no server, no setup.
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Agent
argument-hint: "[--fix]"
---

# /code-watch — two-lens audit, inline

A deeper, on-demand audit than `/pre-commit`. Two passes over the same change:

1. **Security & bugs** — a fixed rubric of things that hurt in production.
2. **Quality** — the project's *own* rules, extracted from its CLAUDE.md (or a
   hand-authored `quality-rules.md`), so you grade against the team's standards
   rather than generic best practice.

Run it for risky changes or before a merge you care about — not on every commit
(that's `/pre-commit`'s job). It does the analysis inline with Claude's own tools;
there is no server to run.

## Steps

### 1. Gather the change

```bash
MAIN="${MAIN:-main}"
AHEAD=$(git rev-list --count "$MAIN"..HEAD 2>/dev/null || echo 0)
if [ "$AHEAD" -gt 0 ]; then
  git diff "$MAIN"...HEAD --stat && git diff "$MAIN"...HEAD
else
  git diff HEAD --stat && git diff HEAD
fi
git diff --staged
```

No changes → say so and stop. For each changed file, **read the full file**, not just
the diff — a three-line change can be wrong because of what surrounds it. For a large
diff (>500 lines), launch parallel Explore agents over file groups.

---

## Pass 1 — Security & bugs

Review every changed file against this rubric. Flag only real issues; cite
`file:line` for each.

- **Authn / authz** — every new entry point (route handler, server action, RPC)
  verifies the caller is authenticated, and checks resource ownership against the
  caller's tenant/account, not just that the resource exists. Role checks are
  server-side, not UI-hidden.
- **Injection** — no raw string interpolation into queries, shell commands, or
  storage paths. Uploads validated by content type and size, filename sanitized.
  User-supplied HTML sanitized by allowlist.
- **Secrets & data exposure** — no keys, tokens, or connection strings in source or
  logs. Sensitive fields not returned in responses unless authorized.
- **Resilience** — no swallowed catch blocks; async work is awaited (no
  fire-and-forget on serverless); loops and polls have timeouts; allocated
  resources (object URLs, handles, connections) are released.
- **Rate limiting** — sensitive operations (auth attempts, bulk reads, LLM calls)
  are limited, and the limiter state is persistent, not in-process memory.

Hold these findings to combine in the final report.

---

## Pass 2 — Quality (project's own rules)

### 2a. Find the rules source, in priority order

1. `./quality-rules.md` (hand-authored, if present)
2. `./CLAUDE.md`
3. `./.claude/CLAUDE.md`

If none exists, **skip this pass**, tell the user ("No quality rules found — add a
CLAUDE.md or a quality-rules.md to enable the quality lens"), and go straight to the
report with security findings only.

### 2b. Extract checkable rules

Read the rules source and pull out the concrete, checkable rules — the team's
standards, stated as things you can verify against a diff. Examples of the *shape*
(yours will differ): "every mutation revalidates affected caches," "types come from
the central types file, not inline," "user-facing lists are sorted," "no new util
file when the shared one already covers it." Keep each rule's source `file:line` so
you can cite which rule a finding violates.

### 2c. Grade the change against those rules

For each extracted rule, check the changed files. Flag violations with `file:line`,
the rule violated **verbatim**, and its source location. Don't invent rules the
project doesn't state — grade against theirs.

---

## Report

Combine both passes:

```
## A. Security & bugs
  [HIGH | MED | LOW] <category> — <title>
  file:line — <what's wrong>
  Fix: <concrete suggestion>

## B. Quality   (omit if pass 2 skipped)
  Rules from <source file> (<hand-authored | extracted>)
  [severity] <title>
  file:line — violates: "<rule verbatim>"  (rule at <source file:line>)
  Fix: <concrete suggestion>

## Triage
  Worth fixing now:  <highest-impact across BOTH lenses first>
  Real but deferrable: <...>
  False positive / acceptable tradeoff: <...>
```

Treat both lenses on equal footing — a high-confidence quality violation can matter
more than a low-severity security nit.

## Auto-fix mode

If `--fix` was passed (check `$ARGUMENTS`) or the user says "fix those": fix
everything you marked **worth fixing now** from both lenses, then run the project's
verification (`npm run build` + test suite, or the stack equivalent) and summarize
what changed and what you left.

## Calibration

- **Be calibrated.** Zero issues on a lens → say so. Don't manufacture findings to
  look thorough. An honest "this is solid" is a valid result.
- **Read full files, not just diffs.** Context decides whether a line is a bug.
- **Don't flag unchanged code** unless the change introduces a dependency on it.
- **Don't review generated files** — lock files, build output, vendored components.
- **Grade against the project's rules, not your priors.** The quality lens is only
  as good as the CLAUDE.md it reads; if a rule is missing there, note it as feedback,
  don't invent it here.
