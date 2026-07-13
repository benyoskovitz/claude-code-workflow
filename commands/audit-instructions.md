---
description: Audit CLAUDE.md files, skills, and command files for vague, unenforceable, or drift-prone instructions. Run periodically to tighten guidance and prevent bugs caused by ambiguity.
---

# Audit Instructions

Audit all instruction files (CLAUDE.md, skills, commands) for quality. The goal is to find instructions that are easy to satisfy superficially while still producing bugs, and tighten them.

## Step 1: Gather all instruction files

Read in full: global CLAUDE.md (`~/.claude/CLAUDE.md`), project CLAUDE.md (`./CLAUDE.md`), every file in `.claude/commands/` (global + project, except this one), all skill files in context, and any memory files.

## Step 2: Evaluate each instruction against these failure modes

For every instruction (bullet, step, or directive paragraph), ask:

**A. Vague scope**, "Could I claim I followed this while only checking one file?" Instructions like "read the code" or "check existing patterns" with no WHERE. *Fix:* replace with a concrete search procedure (the file being modified, its siblings, a grep for the concept).

**B. No verification step**, "How would I know I actually did this?" "Always do X" with no way to confirm X happened. *Fix:* add a verification command or check.

**C. Duplicate source of truth**, "Does this instruction enumerate a list that also exists in code?" Valid values (roles, types, status enums) duplicated from a registry will drift. *Fix:* remove the list, reference the canonical source.

**D. Aspirational without a procedure**, "Tells me WHAT but not HOW." "Check the constraints" with no file to reference or command to run. *Fix:* add the specific file, query, or example to copy.

**E. Ambiguous timing**, "When exactly?" "Always" / "before writing code" without a trigger event. *Fix:* specify the trigger.

**F. Conflicting or redundant**, two instructions saying the same thing (wasted context) or subtly different things about one topic. *Fix:* consolidate into one, in the right place.

**G. Global-project overlap**, project CLAUDE.md duplicating a global rule. *Fix:* remove the duplicate; keep only the project-specific delta.

**H. Memory-CLAUDE.md overlap**, a memory restating a rule already codified in CLAUDE.md (triple-loaded every session). *Fix:* delete the memory; CLAUDE.md is the permanent home.

**I. Stale model-compensation workaround**, "Is this rule fighting a model limitation that no longer exists?" Rules written to counter a past model failure mode (premature stopping, "laziness", needing every step spelled out) become dead weight after a model upgrade. *Fix:* don't auto-delete; flag it with the behavior it targets and re-test on the current model, run the task once WITHOUT the rule and remove it only if the failure mode doesn't recur. Flag-for-human-judgment, never an automatic edit.

**J. Bypassable by rationalization**, "Is this rule clear but routinely talked around?" The rule is specific and verifiable, yet gets skipped via in-the-moment reasoning: "too simple", "it's urgent", "just this once". *Fix:* name the 2-3 likeliest escape hatches next to the rule with a one-line rebuttal each (the rationalization-table pattern from [obra/superpowers](https://github.com/obra/superpowers)), but only where skipping has actually bitten; pre-empting hypothetical excuses is context waste.

## Step 3: Output

Per issue:

```
### [File], Line/Section
**Current:** [exact text]
**Failure mode:** [A-J], [one sentence: how it could be followed superficially]
**Suggested fix:** [rewritten instruction]
```

Group by file. Sort by severity, duplicate-source-of-truth (C) and global-project overlap (G) first, as they most often cause real bugs or waste context.

## Step 4: Summary

Total issues per failure mode (A-J), calling out mode-I candidates separately since each needs a re-test decision rather than a direct fix; the top 3 highest-risk instructions; and any already-well-written instructions worth holding up as the standard.

## Important

- Do NOT add new instructions, only tighten existing ones.
- Do NOT suggest removing an instruction unless it's truly redundant with another.
- Preserve every instruction's intent, change only specificity.
- Skip instructions that are already concrete and verifiable.
- Present findings for review. Do NOT edit files, the user decides which fixes to apply.
