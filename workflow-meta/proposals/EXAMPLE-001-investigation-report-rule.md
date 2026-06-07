# EXAMPLE-001, require an Investigation Report before non-trivial edits

<!--
  Filled-in EXAMPLE of a proposal. Fictionalized and generic. Pairs with
  analyses/EXAMPLE-2026-02-10-plan-before-coding.md and adrs/EXAMPLE-001-...md.
  Your own proposals go alongside it, using TEMPLATE.md.
-->

**Status:** Adopted 2026-02-12
**Motivation:** `analyses/EXAMPLE-2026-02-10-plan-before-coding.md`

## Problem

The agent starts editing before it understands the change. On non-trivial work that produces wrong starts: editing the wrong file, missing a caller, not noticing there was no test coverage. The cost lands after the fact, when I clean it up.

## Proposed change

Add a "maintenance change protocol" section to CLAUDE.md that requires an Investigation Report before any non-trivial edit. The report must exist before the first Edit. It names: files read, the symbol being changed, direct callers and importers (actual grep output, not a summary), tests covering the path, and a task rubric of 3 to 5 binary pass criteria written to `.rubric.md`.

Skip it only for typos, comment-only changes, formatting, and config-value tweaks.

The exact text is in `CLAUDE.md.template` under "Maintenance change protocol."

## Explicit non-goals

- Not requiring it for trivial changes. A typo fix that triggers a full report just trains me to ignore the rule.
- Not auto-generating the rubric. If the report is mechanical box-ticking, it stops being a thinking step. The point is to make the agent actually look before it leaps.

## Alternatives considered

1. **Rely on Plan Mode only.** Rejected. I don't reach for Plan Mode on medium changes, which is exactly where the failures happen.
2. **A pre-edit hook that blocks edits.** Rejected for now. Too blunt; it would fire on trivial edits too. Revisit if the soft rule gets ignored.

## Rollout

Adopted in CLAUDE.md on 2026-02-12. Two-week watch: note whether wrong starts drop and whether the report ever feels like pointless ceremony. Review on 2026-02-26.

## Adopted commits

CLAUDE.md edit (no PR, personal config). Recorded as `adrs/EXAMPLE-001-plan-before-nontrivial-changes.md`.
