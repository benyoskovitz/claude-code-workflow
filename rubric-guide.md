# Task rubric guide

Read this before writing or rewriting a `.rubric.md`. The rule that a non-trivial task gets a rubric lives in `CLAUDE.md.template` ("Task Rubric"). This file holds the procedure, so the rule can stay short in a file that loads every session while the detail loads only when a rubric is being written. Copy it to `~/.claude/rubric-guide.md`, which is where CLAUDE.md's "Before writing ..., read" line and `/assess` look for it.

For any non-trivial coding task (more than a one-line fix), define a **task rubric** during Plan or Investigation, before writing code. The rubric is the contract for what "done" means for *this specific task*. It is distinct from `/pre-commit` (global anti-patterns) and from any project-specific reviewer agent (codebase non-negotiables).

## Format

3 to 5 **MECE pillars** (mutually exclusive, collectively exhaustive: no two pillars check the same thing, and together they cover the whole change), each with a **binary pass criterion**. No 1-to-10 scoring: it is fake precision.

**Collectively exhaustive means: name every top-level directory the change will touch.** A pillar that greps one directory is a proxy for "is every consumer still correct?", and a proxy scoped to `src/` passes while `scripts/` and `docs/` stay wrong. If the change has two workstreams (remove a feature *and* rewrite the tooling that measured it), each gets its own pillar or the second goes ungraded. Pillars are task-specific: a UI change has a different rubric (consistency, cursor-pointer, required-field markers) than a pipeline change (timeout safety, cost, structured-output integrity).

**A criterion names a property, not an example.** "Blocks `git -c user.email=`" can only fail if you forgot a case you had just written down. "Blocks every syntax git accepts for setting a different author" sends the grader to find the cases you did not list. Examples are what you had in mind at Plan time, and the code you write minutes later satisfies them by construction. If a criterion could be satisfied by handling exactly the strings it names, rewrite it. **And the property must generalize the change, not a supporting fact the change leaves untouched.** A criterion whose subject reaches past what the change decides is a rule you are asserting about the codebase. Check it against the project's stated decisions before you write it in.

**Every pillar must be checkable from the repository at the moment `/assess` runs**: the diff, the working tree, and git history, before the commit, before deploy. A criterion needing a deployed environment, a staging run, or production data is a **rubric defect**. `/assess` reports it as an item it cannot settle, which fails the run, because no amount of work on the working tree can ever settle it. Those checks belong in the verification plan or a pre-deploy step. **A pillar asserting anything about an artifact outside the diff (git history, a recovery path, an archived file) must execute the check rather than state it.** "Recoverable from branch history" is a command to run, not a sentence to write.

## Where it goes

Save to `.rubric.md` at the working directory root, not under `.claude/`: Claude Code treats `.claude/` as a sensitive path and blocks writes there even with explicit allow rules. Each worktree has its own working directory, so parallel sessions don't collide. Add `.rubric.md` and `.rubrics/` to `.gitignore`.

**Include a `**Footprint:**` line naming every repo and top-level directory the change touches**, leading with the repo name when it is not the working tree. `/assess` reads it to find the files a `git diff` here cannot see. A change that edits your global config while writing the reasoning up in a separate lab repo is two repos every time.

On `PASS`, `/assess` archives the rubric to the main repo's `.rubrics/`, not a worktree's, with slashes in the branch name flattened to dashes. A worktree's archive is deleted with the worktree, and an unflattened `feature/x` branch makes the move fail.

## Template

```markdown
# Task Rubric: <one-line task description>
**Date:** YYYY-MM-DD
**Branch:** <feature-branch>
**Footprint:** <every repo and top-level dir the change touches>
**Failing rounds:** 0
1. **<Pillar name>**: <binary pass criterion>
```

For a written analysis only (defined below), add a `**Kind:** analysis` line under `Footprint`. It is left out of the template on purpose, because a rubric that carries it switches `/assess` into analysis mode. The author sets it at Scope time, and it changes what `/assess` does on a `FAIL`: one round, then fix in place.

`Failing rounds` is the only field `/assess` writes. It increments on each `FAIL` and feeds the three-round cap below. Start it at 0, and when you rewrite the rubric between rounds **keep the line and its current value**. Dropping the line stops `/assess` at its shape check. Regenerating it from this template's `0` passes that check and quietly restores the unbounded loop.

## The loop

**Then Execute, then `/assess`**, which grades each pillar pass or fail with evidence in a fresh agent that did not write the code, then asks that same agent, with the rubric set aside, what else is wrong.

**Any pillar fails, any criterion it cannot settle, or anything it says must be fixed before this ships**: re-enter Plan mode narrowed to that item. Do NOT patch in place. Patches mask the underlying gap.

**Capped at three rounds.** On the third failing grade of one task, counted in the rubric's `Failing rounds` field, `/assess` stops and asks the user what to do instead of sending the work back to Plan a third time. A capped run is still a `FAIL`: the commit stays blocked and the rubric stays in place, so the cap removes the automatic next cycle, never the failure. It does not apply to `NOT CHECKED`, which means nothing was graded and so is never evidence the change is stuck. **The no-patching rule binds the agent's own choice, not the user's:** at the cap the user may direct a fix in place, and that is an instruction, not the failure mode the rule guards against.

**Only a `PASS`** leads to `/pre-commit`, then commit, then PR.

## A written analysis gets one grading round

An analysis is a task whose whole deliverable is a document that informs a decision (an audit, a comparison, an investigation write-up) and that changes no code, config, prompt or instruction an agent follows. Write a rubric with a `**Kind:** analysis` line, run `/assess` once, then fix every problem it reports in place, including failed items, and list the fixes in the PR body. Do not re-grade and do not re-plan.

A proposal or a rule change is not an analysis. It changes what an agent does, so it keeps the full loop.

## When to skip the rubric

Only for: typos, comment or formatting-only changes, dependency bumps without API changes, generated code, and anything where the Investigation Report is also skipped. "This is small" is the failure mode. When in doubt, write it. Three pillars take a minute.
