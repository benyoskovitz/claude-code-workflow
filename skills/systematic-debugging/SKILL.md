---
name: systematic-debugging
description: >
  Use when a bug, test failure, or unexpected behavior resists the first obvious
  fix, before proposing another one. Enforces root-cause investigation, one
  hypothesis at a time, and a hard stop after 3 failed fix attempts.
user-invocable: true
---

# /systematic-debugging: root cause before fixes

Random fixes waste time and create new bugs. A quick patch that "seems to work" usually masks the real problem, which comes back later wearing a different symptom.

**The rule: no fixes without root-cause investigation first.** If you can't explain *why* the bug happens, you're not ready to propose a fix.

This applies MOST when it's tempting to skip: under time pressure, when the fix "seems obvious," and especially when a previous fix didn't work.

## Phase 1: find the root cause

Before proposing ANY fix:

1. **Read the whole error.** Full message, full stack trace, exact line numbers. Errors often contain the answer; skimming past them is the #1 source of wasted cycles.
2. **Reproduce it reliably.** What exact steps trigger it? Every time, or sometimes? If you can't reproduce it, gather more data. Don't guess.
3. **Check what changed.** Recent commits, new dependencies, config edits, environment differences. Most bugs are recent changes wearing a disguise.
4. **Trace the bad value to its source.** Where does the wrong data originate? What called this with the bad value? Keep walking up until you find where it first goes wrong. Fix there, not where the error surfaced.

**For multi-part systems** (hook → script → API, or CI → build → deploy): before proposing anything, add one round of logging at each boundary showing what goes in and what comes out. Run once. The logs tell you *which* layer breaks; then investigate that layer only. This is faster than guessing at layers.

## Phase 2: one hypothesis at a time

1. **State it explicitly:** "I think X is the root cause, because Y." Specific, written down, before touching code.
2. **Test it with the smallest possible change.** One variable at a time. Never bundle multiple fixes: if it works you won't know which one did it, and if it fails you've added noise.
3. **Verify before stacking.** Fix worked? Confirm the original symptom is gone, then move on. Didn't work? Form a NEW hypothesis. Do not pile another fix on top of the failed one.
4. **If you don't understand something, say so.** "I don't understand why X happens" followed by more investigation beats a confident guess every time.

## Phase 3: fix it properly

1. If a test framework exists, write a failing test that reproduces the bug first (or a one-off repro script if not). It proves you understand the cause and stops the bug from coming back.
2. Fix the root cause. One change. No "while I'm here" improvements bundled in.
3. Confirm: repro now passes, nothing else broke, and the original symptom is actually gone (fresh run, not memory of an earlier run).

## The 3-strikes rule

**After 3 failed fix attempts, STOP. Do not attempt fix #4.**

Three failures means this is probably not a bug hunt anymore. It's a sign the approach or architecture is wrong. Telltales: each fix reveals a new problem somewhere else, or every fix seems to need a big refactor to work.

At that point, step back and raise it with the user: here's what was tried, here's what each attempt revealed, here's why the underlying design (not the code) looks like the problem. That conversation is cheaper than fixes #4 through #9.

## Red flags: if you catch yourself thinking any of these, return to Phase 1

- "Just try changing X and see if it works"
- "It's probably X, let me fix that" (without evidence)
- "Quick fix for now, investigate later"
- "Let me change several things at once and re-run"
- "One more fix attempt" (when 2+ have already failed)
- Listing fixes before having traced the data flow

Simple-looking bugs have root causes too, and the process is fast for simple bugs: Phase 1 for a typo-level bug takes a minute. Skipping it only ever saves time on bugs you'd have fixed anyway.

## When there's genuinely no root cause

If investigation shows the issue is truly environmental or timing-dependent (flaky network, a race in a third-party service): document what you ruled out, add appropriate handling (retry, timeout, clear error), and add logging so the next occurrence carries evidence. But be honest: most "no root cause" conclusions are incomplete investigation.

---

*Adapted from the `systematic-debugging` skill in [obra/superpowers](https://github.com/obra/superpowers) (MIT, Jesse Vincent), trimmed to about a third of its length and rewritten. This is the one file in this repo that's a derivative work rather than an original implementation of a borrowed idea.*
