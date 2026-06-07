Audit the current project's setup and report a prioritized list of gaps with suggested fixes. Work through each section, then produce a single consolidated report.

## 1. CLAUDE.md quality

Read the project's CLAUDE.md. Check whether it includes each of these; report PRESENT or MISSING with a one-line note:

- **Project overview**: what it does, in 1-2 sentences
- **Tech stack**: frameworks, languages, key dependencies
- **Build & test commands**: build, test, lint, dev server
- **Directory structure**: where key code lives
- **Current state**: what phase, what's implemented vs stubbed
- **Known constraints**: guardrails, things NOT to do
- **Environment setup**: env vars, services, new-dev steps

If CLAUDE.md doesn't exist, flag that as the top-priority gap.

## 2. Directory structure vs documentation

Compare what CLAUDE.md says about structure against the actual tree (Glob/ls). Flag: directories documented but missing on disk; significant directories present but undocumented (skip `node_modules`, build output); any mismatch.

## 3. Slash commands & skills

List everything in `.claude/commands/` and `~/.claude/commands/` (and skills). Summarize each in one line. Then assess workflow coverage, flag if any of these are missing a command, but only if relevant to this project's stack: **commit** (pre-commit/commit helper), **test** (running or writing tests), **deploy** (pre-deploy checks), **review** (code review), **debug** (structured debugging).

## 4. Hook coverage

Read `.claude/settings.json` and `~/.claude/settings.json` if present. Check for: pre-commit hooks (quality checks before commits), post-edit hooks (lint/format/typecheck nudges), permission allow-lists (too broad = security risk; too narrow = friction), and missing quality gates for the project's stack.

## 5. Outstanding debt

Search the codebase for: `TODO`/`FIXME` (list with path + text), `HACK`/`WORKAROUND`, skipped tests (`.skip`, `xit`, `xdescribe`), `@ts-ignore`/`@ts-expect-error` (count + locations), `eslint-disable` (count + locations), leftover `console.log` debugging, and doc markers like `[TODO]`/`[STUB]`/`[PLACEHOLDER]`.

## Output

### Project Health Report

**Overall:** [HEALTHY / NEEDS ATTENTION / SIGNIFICANT GAPS]

**Priority fixes** (ordered by impact):
1. [highest-impact gap], what to fix and why
2. ...

**Section details:** the findings from each section above, with PRESENT/MISSING/OK/FLAG labels for easy scanning.

Keep it actionable. Every gap gets a concrete suggested fix, not just a warning.
