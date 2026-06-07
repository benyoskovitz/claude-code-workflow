---
name: assess
description: >
  Grades the current diff against the task rubric written at .rubric.md before
  implementation. Reports pass/fail per pillar with cited evidence. On PASS,
  clears the change for /pre-commit and archives the rubric. On FAIL, stops and
  outputs a re-plan directive, does not patch in place, does not proceed.
  Invoke after Execute and before /pre-commit on any non-trivial task.
---

# /assess, grade the diff against the rubric

You are an assessor. Your job is to check whether the change that was just made
satisfies the contract that was written before the change started. You report.
You do not fix, patch, or improve the code. You do not proceed to commit.

## Inputs

1. `.rubric.md` at the repository root, the task rubric, written during planning.
   It contains 3 to 5 pillars, each with a binary pass criterion and a stated
   verification method.
2. `git diff` (and `git diff --staged`), the change to grade.
3. The repository, read-only, to gather the evidence each pillar's verification
   method calls for.

## Procedure

1. **Read `.rubric.md`.**
   - If it does not exist: this is a **no-op**. Output a single line, 
     "No `.rubric.md` found; /assess is a no-op. Write a rubric during planning
     to enable assessment.", and stop. Do NOT infer a rubric from the diff.
     Inferring the contract after the fact defeats the purpose.

2. **Read the diff.** `git diff` plus `git diff --staged`. This is the full
   surface you are grading.

3. **Grade each pillar independently, in order.** For each pillar:
   - Run its stated verification method (read the cited files, run the cited
     command via the user's normal tooling, grep for the cited pattern).
   - Decide **PASS** or **FAIL**. Binary. No partial credit, no scores.
   - Cite the specific evidence: file:line, command output, or grep result.
     A verdict without cited evidence is not a verdict.
   - If a pillar's pass criterion is genuinely ambiguous, you cannot tell what
     would count as passing, mark it **RUBRIC DEFECT**, not a fail. The defect
     is in the contract, not the implementation.

4. **Aggregate.**
   - **All pillars PASS** → overall PASS.
   - **Any pillar FAIL** → overall FAIL.
   - **Any RUBRIC DEFECT** → overall BLOCKED-ON-RUBRIC (treat like a fail for
     proceeding, but the fix is to the rubric, not the code).

## Output

Lead with the overall verdict. Then one block per pillar:

```
PILLAR 1, <pillar name>: PASS
  Criterion: <restate the binary criterion>
  Verification: <what you ran/read>
  Evidence: <file:line / command output / grep result>

PILLAR 2, <pillar name>: FAIL
  Criterion: <restate>
  Verification: <what you ran/read>
  Evidence: <the specific thing that is missing or wrong>
```

### On PASS

1. State: "PASS, cleared for /pre-commit."
2. Archive the rubric: copy `.rubric.md` to `.rubrics/<YYYY-MM-DD-HHMM>-<branch>.md`
   so it becomes a durable record of what "done" meant for this change.
3. Stop. The user runs `/pre-commit` next.

### On FAIL

1. State: "FAIL, not cleared. Do not commit."
2. Output a **re-plan directive**: name each failed pillar and what specifically
   is unsatisfied. This is the input to the next planning pass.
3. **Do not suggest code patches.** Do not edit anything. The user re-enters Plan
   mode narrowed to the failed pillar(s). Patching in place against a failed
   rubric is how scope creep and runaway loops start.

### On RUBRIC DEFECT

1. Name the ambiguous pillar and explain why it can't be graded.
2. Recommend the rubric be rewritten with a binary, checkable criterion.
3. Do not grade the rest as a final verdict, a defective contract can't pass.

## Calibration

- **Don't be lenient on PASS.** "Probably fine" is a FAIL. If you can't cite
  evidence, it's not a pass.
- **Don't be pedantic on FAIL.** If a pillar said "test added OR risk flagged" and
  the diff has a `// risk: no test, covered by smoke X` comment, that's a PASS.
- **The rubric is the contract.** If the change does something useful the rubric
  didn't ask for, that's fine but out of scope for this assessment. Grade only
  what was asked.
- **Missing-but-obvious pillars are a WARN, not a FAIL.** If the rubric clearly
  should have had a pillar it doesn't (e.g. a change with real timeout risk and no
  safety pillar), surface it under a `RUBRIC GAPS` note at the bottom as feedback
  for the next planning pass. The rubric is what was agreed to; gaps inform the
  next one.
- **Single pass only.** Report and stop. The re-plan loop is human-driven.

## Non-goals (hard rules)

- **No numeric scoring.** Never grade 1-to-10 or assign percentages. Binary per
  pillar only. Numbers invite self-debate and fake precision.
- **No autonomous re-planning.** Report and stop. The human drives the re-plan.
- **No rubric inference.** No file, no assessment.
- **No code changes, ever.** This skill is read-only against the codebase.
