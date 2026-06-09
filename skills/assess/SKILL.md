---
name: assess
description: >
  Grade the current diff against the task rubric written at .rubric.md before
  implementation. Grading runs in a fresh, independent sub-agent so the agent that
  wrote the code is not the one certifying it. On PASS, clears the change for
  /pre-commit and archives the rubric. On FAIL, outputs a re-plan directive and
  stops, never patches in place. Run after Execute, before /pre-commit.
user-invocable: true
allowed-tools: Task, Bash, Read, Grep, Glob
---

# /assess: grade the diff against the rubric

This is the gate between doing the work and committing it. It checks whether the
change that was just made satisfies the contract (`.rubric.md`) that was written
before the change started. It reports. It does not fix, patch, or improve code,
and it does not proceed to commit.

The important design choice: **the grading happens in a separate sub-agent.** The
agent that wrote the code must not be the agent that certifies it. A self-grade
just confirms its own reasoning, especially on judgment-call pillars. So this skill
spawns a fresh grader that sees only the rubric and the diff, with none of this
session's implementation context, and takes its verdict as the assessment.

## Steps

### 1. Locate the rubric

```bash
test -f .rubric.md && cat .rubric.md
```

If it does not exist, output `No rubric found at .rubric.md. /assess is a no-op without a task rubric written before implementation.` and stop. Do NOT invent a rubric after the fact; that defeats the purpose.

### 2. Get the diff

```bash
git diff --staged HEAD
git diff HEAD
```

Combine them. If both are empty, output `No changes to assess.` and stop.

### 3. Grade in an independent sub-agent

**Do NOT grade the rubric yourself.** Spawn a fresh general-purpose sub-agent (the
Task tool, `subagent_type: "general-purpose"`) with the prompt below, substituting
`<RUBRIC>` with the verbatim contents of `.rubric.md` from step 1. Everything
between the fences is the sub-agent's prompt:

---
You are an independent rubric grader. You did NOT write this code. Your job is to
certify whether the current change satisfies its task rubric, skeptically and on
evidence only. You read and report. You never modify, create, or delete files.

The task rubric:

<RUBRIC>

Steps:
1. Run `git diff --staged HEAD` and `git diff HEAD`. Combine them. That, plus the
   current working tree, is all you may rely on. Do not assume intent that isn't
   visible in the diff or tree.
2. For each pillar, read the pass criterion verbatim and verify it:
   - Prefer concrete checks (grep for a pattern, read a specific file) over
     judgment. If a criterion is too vague to verify deterministically, mark it
     AMBIGUOUS (a rubric defect, not an implementation defect).
   - PASS requires citing the file:line that satisfies the criterion. "Probably
     fine" with no citable evidence is a FAIL.
   - FAIL cites the file:line that violates it, or "no evidence found in diff" if
     the criterion required an addition that was not made.
   - Don't be pedantic: if a criterion was "test added or risk flagged" and the
     diff has a `// risk: no test, covered by smoke test X` comment, that's a PASS.
   - If a pillar needs more than a few greps/reads to verify, mark it AMBIGUOUS
     rather than crawling the codebase. That vagueness is a rubric defect.
3. Return ONLY the report in this exact shape, no preamble, no sign-off:

   TASK RUBRIC ASSESSMENT
   ======================
   Task: <one-line description from rubric>

   PASS  Pillar 1: <name>
     Criterion: <verbatim>
     Evidence: <file:line or finding>

   FAIL  Pillar 2: <name>
     Criterion: <verbatim>
     Evidence: <file:line or "no evidence found">
     Gap: <one line: what is missing>

   AMBIGUOUS  Pillar 3: <name>
     Criterion: <verbatim>
     Issue: <why this cannot be verified deterministically>

   RUBRIC GAPS (optional, WARN only):
     <a pillar that should obviously exist but the rubric omits>

   Result: <PASS: N of N passed | FAIL: N of M passed | RUBRIC DEFECT: N ambiguous>
---

Take the sub-agent's returned report as the assessment. Do not re-grade it or
override it. If it came back in the wrong shape, re-invoke once with a correction;
do not silently substitute your own grade. Surface the report to the user verbatim,
then act on the `Result:` line in step 4.

### 4. Handle the result

**All pillars PASS:**
1. State "PASS. Cleared for /pre-commit."
2. Archive the rubric so there's a durable record of what "done" meant:
   `mkdir -p .rubrics && mv .rubric.md .rubrics/$(date +%Y-%m-%d-%H%M)-$(git branch --show-current).md`
3. Stop. The user runs `/pre-commit` next.

**Any pillar FAILs:**
1. State "FAIL. Not cleared, do not commit."
2. Output this directive verbatim:

   ```
   RE-PLAN REQUIRED

   A failed pillar means re-entering Plan mode narrowed to the failed pillar(s)
   above. Do NOT patch in place; patches mask the underlying gap.

   Produce a focused plan for the failed pillar(s) only:
   - What is the minimum change to satisfy this pillar?
   - What did the original plan miss?
   - Are there related call sites the original plan also missed?

   Update .rubric.md only if the pillar itself was wrong; otherwise leave it and
   iterate on the implementation.
   ```
3. Do NOT proceed to `/pre-commit`. Do NOT suggest a quick fix.

**RUBRIC DEFECT (pillars AMBIGUOUS, none failed):**
1. State "RUBRIC DEFECT. Cannot certify done."
2. Suggest tightening the ambiguous pillar(s) into binary, checkable criteria at
   the next planning step. Do not proceed.

## Non-goals (hard rules)

- **No numeric scoring.** Binary per pillar. Numbers invite self-debate and fake
  precision.
- **No self-grading.** The grade comes from the independent sub-agent, not from the
  agent that wrote the code.
- **No autonomous re-planning.** Report and stop. The human drives the re-plan.
- **No rubric inference.** No `.rubric.md`, no assessment.
- **No code changes, ever.** Read-only against the codebase.

## Why a separate grader

The rubric solves half the problem: it stops the AI from grading against a standard
it invented after the fact. The independent sub-agent solves the other half: it
stops the AI from grading its *own work*. The writer is invested in its own
reasoning and will wave through a judgment-call pillar it would fail in someone
else's diff. A fresh grader with no implementation context can't. The idea is
SPEAR-inspired (define a contract before you build); the binary-not-scored grading
and the separate grader are deliberate changes to it.
