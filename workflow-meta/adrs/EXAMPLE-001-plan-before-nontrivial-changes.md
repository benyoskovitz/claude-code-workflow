# EXAMPLE-001, plan before non-trivial changes

<!--
  Filled-in EXAMPLE of an ADR (Architectural Decision Record for your workflow).
  Fictionalized and generic. Closes the lifecycle started in
  analyses/EXAMPLE-2026-02-10-plan-before-coding.md and
  proposals/EXAMPLE-001-investigation-report-rule.md.
-->

**Status:** Adopted
**Date:** 2026-02-12

## Context

The agent was starting edits before understanding the change, producing recurring wrong starts on non-trivial work. The cost showed up after the fact, in cleanup. Nothing in the workflow caught a bad assumption at the point it was cheapest to catch: the start.

## Decision

**Require an Investigation Report before any non-trivial edit.** The report must exist before the first Edit, and it ends with a task rubric written to `.rubric.md`. Trivial changes (typos, comments, formatting, config values) are exempt.

## Alternatives considered

1. **Plan Mode only.** Rejected. Not reached for on medium changes, which is where the failures cluster.
2. **A hard pre-edit hook.** Rejected for now. Too blunt; revisit if the soft rule is ignored.

## Consequences

**What works better now:**
- Wrong starts on medium changes dropped noticeably in the first two weeks.
- The report's "callers and tests" section catches missing coverage before the edit, not after.
- The rubric falls out of the same step for free, so `/assess` always has something to grade.

**What's harder or worth watching:**
- On the smallest "non-trivial" changes the report can feel like ceremony. Watch for it becoming box-ticking. If it does, tighten the "skip it for" list rather than dropping the rule.

## Related

- Source analysis: `analyses/EXAMPLE-2026-02-10-plan-before-coding.md`
- Proposal: `proposals/EXAMPLE-001-investigation-report-rule.md`
- The adopted rule lives in `CLAUDE.md.template` under "Maintenance change protocol."
