# 2026-02-10, plan before coding (worked example)

<!--
  This is a filled-in EXAMPLE of an analysis, so you can see what a real lab entry
  looks like. It's fictionalized and generic. Your own analyses go alongside it,
  using TEMPLATE.md. Delete this once you've got the hang of it.
-->

**Source:** my own observation this week, plus the "plan before you code" advice that shows up in most agent-workflow write-ups.

## What I noticed

Three times this week the agent jumped straight into editing on a change that wasn't trivial, and twice it edited the wrong file first because it hadn't checked who else used the code. I cleaned up the mess after the fact each time. That's reactive. The cost of a wrong assumption is highest at the start, and I'm currently doing nothing to catch it there.

## The claim I'm testing

That forcing a short "investigation" step before any non-trivial edit (what changed, who calls it, what tests cover it, what done means) prevents most of these wrong starts, and costs only a couple of minutes up front.

## How it compares to what I do now

Right now I have nothing. I rely on the agent's judgment about when to plan, and that judgment is inconsistent on small-to-medium changes. Plan Mode exists but I only reach for it on big work. The gap is the medium change: too small to feel like it needs a plan, big enough to go wrong silently.

## Verdict

Worth a proposal. The fix is cheap (a required pre-edit checklist), the failure it prevents is real and recurring, and it composes with the rubric idea (the checklist's last line can be the rubric). See `proposals/EXAMPLE-001-investigation-report-rule.md`.
