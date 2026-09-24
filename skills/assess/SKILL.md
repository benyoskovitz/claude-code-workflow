---
name: assess
description: >
  Grade the current change against the task rubric written at .rubric.md before
  implementation, in a fresh sub-agent that did not write the code, and ask that same
  agent what is wrong outside the rubric. A failed item, an item it cannot settle, or
  anything that must be fixed before shipping blocks the commit and sends the work back
  to Plan, never a patch in place, except a written analysis, which is fixed in place
  after one round. On the third failing grade of one task the loop stops and asks the
  user instead. Run after Execute, before /pre-commit.
user-invocable: true
allowed-tools: Agent, Bash, Read
---

# /assess: did we build what the plan said?

This is the gate between doing the work and committing it. The order is: rubric, then
Execute, then **`/assess`**, then `/pre-commit`, then commit. It reports. It does not fix,
patch, or improve anything, and it does not proceed to commit.

Two questions, one grader, three outcomes. Before any grading there are four stops: no
rubric, a rubric missing its `Footprint` or `Failing rounds` line, no change, or a repo named
in the rubric that isn't on disk.

## 1. Find the rubric

Read `.rubric.md`. If it isn't there, output
`No rubric found at .rubric.md. /assess is a no-op without a task rubric written before implementation. (See ~/.claude/rubric-guide.md.)`
and stop. Never write one now: a rubric invented after the code defeats the point.

**Note the `**Failing rounds:**` line.** It counts rounds on this task that already came back
`FAIL`. Step 1 checks only that it is there. Step 5 is the only place its value is read for a
decision and the only place it is written, and it increments on `FAIL` alone. So a run that
stops in step 1 or 2 costs nothing, and neither a `PASS` nor a `NOT CHECKED` spends a round.

**Check the rubric's shape before anything else**, with Bash:

```bash
python3 - <<'PY'
import io, re
s = io.open(".rubric.md", encoding="utf-8").read()
need = {"Footprint": r"^\*\*Footprint:\*\*[ \t]*\S", "Failing rounds": r"^\*\*Failing rounds:\*\*[ \t]*\d+[ \t]*$"}
miss = [k for k, pat in need.items() if not re.search(pat, s, re.M)]
print("RUBRIC SHAPE OK" if not miss else "RUBRIC MALFORMED: missing or misshapen " + ", ".join(miss))
PY
```

If it prints `RUBRIC MALFORMED`, output that line and this, then stop without grading:
`Read ~/.claude/rubric-guide.md and add the missing line. If the rubric was rewritten after a failed round, restore the Failing rounds value it had before the rewrite; do not start it at 0.`
A missing `Footprint` sends the grader into one repo when the change may span two. A missing
count is how a rewrite between rounds loses it. This check sees only that the line exists: a
rewrite that writes the wrong number passes it. If the command errors, say so and stop. Do not
grade a rubric whose shape is unknown.

## 2. Work out what changed

Usually `HEAD` is the right starting point. But if any part of this task is **already
committed**, start from the commit before that one instead. A parallel session or a config
sync that runs `git add -A` can sweep your in-flight files into its own commit under an
unrelated subject line.

```bash
git log --oneline -6          # any of these carrying this task?
```

A commit carries this task even when its subject is about something else. Read it with
`git show --stat <sha>` if the subject doesn't say. If you still can't tell, treat it as part
of the change: starting too early only shows the grader extra context, while starting too late
hides the change, and only that failure is silent.

Then, with that value written in:

```bash
BASE=REPLACE_WITH_RESOLVED_START_POINT
git rev-parse --verify --quiet "$BASE" >/dev/null || { echo "resolve the start point first (step 2)"; exit 1; }
git diff --staged "$BASE"
git diff "$BASE"
git ls-files --others --exclude-standard
```

**The third command is not optional.** `git diff` never lists brand-new files, so a change made
entirely of new files looks like no change at all. A new skill, a new hook, a new doc: that is
an ordinary shape, not an edge case. The change is empty only when all three come back empty,
and `.rubric.md` itself doesn't count.

If it is empty in **every** repo in scope, output `No changes to assess.` and stop. Check the
other repos before stopping: a change can leave this tree clean while all of it sits in another
one.

The block ships a placeholder rather than a `HEAD` default on purpose. A wrong start point runs
clean and answers the wrong question. The placeholder fails loudly instead.

**If the change touches another repo, that repo is part of it.** A `git diff` here sees only
this one. The rubric's `Footprint:` line names the rest. Resolve each to a path, work out its
own start point the same way, and give the grader the path, the start point, and the diff
command for each, in the `git -C <path> diff <that repo's start point>` form. A sub-agent's
shell starts in *your* working directory, so a bare `git diff` there reads the wrong tree.
**A path you cannot resolve stops the run** rather than being guessed at: output
`Cannot resolve <path>: named in the rubric's Footprint but not on disk.` and stop, leaving
`.rubric.md` where it is.

## 3. Grade it in a fresh agent

**Never grade this yourself.** You wrote the code, so you cannot certify it. Spawn one
`general-purpose` agent with the `Agent` tool. Invoking this skill is the user requesting that
agent, so spawn it without asking.

Give it: the rubric verbatim, the start point you resolved, the three commands above, the list
of new files, and every extra repo with its own start point. Ask it two things, in this order:

1. **For each rubric item, pass or fail.** A pass cites the file and line that satisfies it.
   "Probably fine" with nothing to cite is a fail. A fail cites the file and line that violates
   it, or says nothing in the change does this. If an item claims something runs or passes, run
   it and quote the output rather than trusting a report. Don't be pedantic: if the item was
   "test added or risk flagged" and a comment flags the risk, that passes. If an item **cannot
   be settled from the repository at all** (no determinate answer, or only a deployed
   environment could produce one), say so. That is a broken rubric item, and it is neither a
   pass nor a fail.
2. **Now set the rubric aside. What else is wrong?** Anything it didn't ask about. If the change
   is written instructions rather than code, trace what an agent following them would actually
   do, step by step, and find a state they don't cover, cover twice, or route to two different
   answers. If you find nothing, say so and list what you tried. An empty answer with no
   attempts listed is not a clean result.

   **Rate each problem: must be fixed before this ships, yes or no.** This is the only thing
   that can fail a run when every item passes, so it needs a test rather than a feeling. Answer
   yes only if you can **name an ordinary use that hits it**. If you cannot name one, or you
   genuinely cannot decide, answer no and say it was close. Nothing is lost by a no: every
   problem reaches the user in full either way, and a yes returns a working change to Plan.
   Judge it against what the change is **for**. Give the grader one line saying that, quoted
   from the task's own statement of purpose (the ticket, the proposal, the user's own words)
   rather than from your account of what you built, and print that line with its source in
   step 5. A yardstick nobody can see cannot be challenged, and one narrowed to what you
   happened to build makes every problem non-blocking.

Tell the grader the `**Failing rounds:**` line is bookkeeping rather than an item, and that how
many rounds came before must not weigh on any verdict.

Tell it to read and report only, never to modify files, and not to read anything under
`.rubrics/`, which holds other tasks' outcomes. A grader that has seen priors is anchored by
them. The one exception: if the change cites an archived rubric by path, the grader may open
that one file, at the cited passage only.

**Ask for this exact shape**, because step 4 has to read it and because a shapeless answer is
how a half-finished grade slips through:

```
RUBRIC
  Item <n>: PASS | FAIL | CANNOT SETTLE: <name>
    Evidence: <file:line, or what is missing, or why nothing can settle it>
  ... one block per item, every item in the rubric, in order

OTHER PROBLEMS
  <problem>: <the trace, or the input used and what came back>
    Must fix before shipping: yes | no, <reason>
  ... or "none found, tried: <list>"

COUNTS: <P> passed, <F> failed, <C> cannot settle, of <M> items; <K> other problems, <Y> must-fix
```

**And tell it not to write an overall verdict.** The counts are counts. The outcome is composed
once, in step 4. A grader's own "this looks fine overall" sitting above a composed `FAIL` is two
answers in one report.

Take its answer as the grade. Do not re-grade it or override it. If it comes back unreadable,
ask once more. If it's still unreadable, the outcome is `NOT CHECKED`.

## 4. One outcome

**First check that the answer is complete, on both halves.** Count the item blocks and compare
with the number of items in `.rubric.md`. Then confirm the `OTHER PROBLEMS` block came back at
all, either with problems in it or with `none found` and a list of what was tried. Either half
short gets the same one re-ask an unreadable answer gets. Still short after that is
`NOT CHECKED`.

Both halves matter for the same reason. A report grading three of five items, all passing, is
readable and trips no failure row below, so it would otherwise compose `PASS` over two items
nobody looked at. A report with every item passing and no `OTHER PROBLEMS` block drops the only
route to `FAIL` when every item passes.

Then, first match wins:

| Outcome | When |
| --- | --- |
| `NOT CHECKED` | no usable answer from the grader, it graded no items, it returned fewer item blocks than the rubric has items, **or it returned no `OTHER PROBLEMS` block** |
| `FAIL` | any item failed, any item cannot be settled, or any problem must be fixed before shipping |
| `PASS` | neither of the above |

`NOT CHECKED` comes first because every other row is a negative: with no answer there are no
failures, and the table would otherwise pass a change nobody looked at.

Then compose one line. **Do not print it here.** Step 5 prints it, once, after the summary and
the verbatim block:

```
Result: <PASS | FAIL | NOT CHECKED>. N of M items passed, K other problem(s)<, reason>
```

`K` is always stated, `0` included. `reason` is required on `FAIL` and names the route:
`item 3 failed`, `item 3 cannot be settled`, or `"<short name>" must be fixed first`.

## 5. Say what happened, then act

First, in your own plain words: the outcome, then what each failure means for someone using
this thing. Include **every** problem the grader found, including the ones marked "no". Then
the grader's answer verbatim underneath, unedited, as the record, inside a fenced code block
(a writing hook that skips fenced text will then leave the record alone). Then the Result line.

Translating a verdict is not re-grading it. Never change a pass, a fail, or a must-fix answer.
If you disagree, say so as your own note beneath the block.

**On `FAIL`, increment the count before you write anything else**: before the summary, before
the verbatim block, before the Result line. It is one command and it decides which branch below
you take. Putting it last means a run that ends the moment the user reads the verdict loses the
round. **Run it with Bash.** `Edit` and `Write` are not in this skill's `allowed-tools`, so
reaching for them is refused and the count silently stays put, which makes the cap inert.

```bash
python3 - <<'PY'
import io, re, sys
p = ".rubric.md"
s = io.open(p, encoding="utf-8").read()
m = re.search(r"^\*\*Failing rounds:\*\*[ \t]*(\d+)[ \t]*$", s, re.M)
if m:
    n = int(m.group(1)) + 1
    s = s[:m.start()] + f"**Failing rounds:** {n}" + s[m.end():]
elif "Failing rounds" in s:
    sys.exit("MALFORMED: a Failing-rounds line exists but is not `**Failing rounds:** <n>`. "
             "Fix it by hand; do not guess the count.")
else:
    n = 1
    lines = s.split("\n"); lines.insert(1, "**Failing rounds:** 1"); s = "\n".join(lines)
io.open(p, "w", encoding="utf-8").write(s)
print(f"Failing rounds: {n}")
PY
```

**Read the number it prints** and use that, not your own count of the conversation. **If it
errors or prints nothing, print `RE-PLAN REQUIRED`, say the count is unknown, and say why.**
Never assume 1 and never assume the cap. Let the user decide whether this was the third round.
A cap that silently never fires is the failure this counter exists to prevent.

**On `FAIL` or `NOT CHECKED`:** leave `.rubric.md` where it is. Do not run `/pre-commit`. Do not
suggest a quick fix, **except in the capped menu below**, which offers one because the user is
choosing it rather than the agent proposing it, **and except an analysis, next.**

**If the rubric carries `**Kind:** analysis`**, a `FAIL` does not send the work back to Plan, and
neither the `RE-PLAN REQUIRED` block nor the round cap below applies. Increment the count as
usual and report in full as usual. Then print this instead of `RE-PLAN REQUIRED`:

```
FIX IN PLACE (analysis): fix every problem above, list the fixes in the PR body,
and do not re-run /assess.
```

After the fixes, archive the rubric with the `On PASS` command below, then print
`Ready for /pre-commit.` The archived `**Failing rounds:** 1` records that it was fixed in place,
not passed. `NOT CHECKED` on an analysis is handled as for any rubric: re-ask. What counts as an
analysis, and why it gets one round, is in `~/.claude/rubric-guide.md`.

If the count it printed is **1 or 2**, output this verbatim:

```
RE-PLAN REQUIRED

This change goes back to Plan mode, narrowed to what failed above. Do NOT patch
in place: patches mask the underlying gap.

Produce a focused Plan for those items only:
- What is the minimum change to satisfy that item, or to close that problem?
- What did the original plan miss?
- Are there related call sites the original plan also missed?

If a rubric item was itself wrong, update .rubric.md. If nothing failed but a
problem must be fixed first, the rubric is missing an item that would have caught it.
Add one. Otherwise leave .rubric.md alone and iterate on the implementation.
Keep the Failing rounds line and its current value in any rewrite.
```

**If the count it printed is 3 or more**, the loop stops and the decision goes to the user.
Output the block below **instead of** `RE-PLAN REQUIRED`, filling in the outstanding items from
this round's report. Nothing else about the run changes: the outcome is still `FAIL`,
`.rubric.md` still stays where it is, and `/pre-commit` still does not run.

**The cap is a stop, not a pass.** Never call a capped run ready, never archive the rubric on
one, and never soften a failed item or a must-fix answer to get under the cap. What the cap
removes is the automatic next trip through Plan, not the failure.

```
ROUND CAP REACHED. YOUR CALL

Round <N> and this still fails, so /assess stops here rather than sending the work back to
Plan again.

Still outstanding:
- <one line per failed item, per item that cannot be settled, and per must-fix problem>

The commit is still blocked. You can tell me to keep going on these, to fix them in place and
re-grade, to accept them as known and ship anyway, or to drop the change. Which?
```

**"Keep going" buys one more round and then this block prints again.** Nothing resets or
decrements the count, so every round past the cap returns to the user. Say so when you offer
it, or it reads as a one-time gate. **"Ship anyway" leaves the rubric in place.** Never archive
a capped one.

**Fixing in place is the user's to authorise, not the agent's to choose.** The rule against
patching instead of re-planning still binds the agent. What the cap adds is that the user may
direct a fix in place.

**The cap does not apply to `NOT CHECKED`**, at any round, and that outcome does not increment
the count. It means nothing was graded, so stopping there would ship an ungraded change, and
counting it would let two unreadable answers cap a task that has failed once. Re-ask instead,
however many rounds have passed.

On `NOT CHECKED`, say plainly which route it was. There are four: the grader could not be
spawned, so nothing was graded; its answer was unreadable after one re-ask; it graded only some
of the items, in which case say how many of how many; or it answered the items and dropped
question 2, in which case say that nothing looked for problems outside the rubric. Never
self-grade to fill the hole.

**On `PASS`:** archive first, then say it's ready. The archive can fail, and a readiness line
already printed cannot be retracted.

```bash
REPO=$(git rev-parse --show-toplevel)
case "$REPO" in */.claude/worktrees/*) REPO="${REPO%%/.claude/worktrees/*}";; esac
mkdir -p "$REPO/.rubrics"
DEST="$REPO/.rubrics/$(date +%Y-%m-%d-%H%M)-$(git branch --show-current | tr / -).md"
mv .rubric.md "$DEST" && echo "archived: $DEST" || echo "ARCHIVE FAILED: $DEST"
```

Three things in that block matter. `tr / -` flattens the slash in a `feature/<name>` branch,
which otherwise makes the filename a path into a directory nothing created, and `mv` fails.
Stripping the worktree segment puts the archive in the main repo, because a worktree's archive
is deleted with the worktree. And the `||` swallows `mv`'s exit code, so the failure exists only
in that string.

Read the output before printing anything else. On `archived:`, print `Ready for /pre-commit.`
On `ARCHIVE FAILED:`, say so and stop. The verdict is still `PASS`, but the rubric is still at
the tree root.

## Non-goals (hard rules)

- **No numeric scoring.** Binary per item. Numbers invite self-debate and fake precision.
- **No self-grading.** The grade comes from the fresh grader, not from the agent that wrote the
  code. This is the one rule in this file that must never be relaxed.
- **No autonomous re-planning.** Report and stop. The user drives the re-plan.
- **No unbounded loop.** Three failing rounds, then the user decides.
- **No rubric inference.** No `.rubric.md`, no assessment.
- **No code changes, ever.** Read-only against the codebase, apart from the `Failing rounds`
  counter and the archive move.

## Why it works this way

**A separate grader.** The rubric stops the agent grading against a standard it invented after
the fact. The fresh grader stops it grading its *own work*. The writer is invested in its own
reasoning and will wave through a judgment call it would fail in someone else's diff.

**One grader asked two questions.** Grading each item catches what the plan named. "What else
is wrong?" catches what the plan missed, which is where most real bugs live. A must-fix answer
fails the run only when the grader can name an ordinary use that hits it, so the second
question adds blocking power without turning every nitpick into a re-plan.

**A cap at three rounds.** Declining automatic re-planning guards against a runaway loop on a
misspecified rubric, but the re-grade loop itself had no bound. In the history this was
adopted from, a few tasks ran far past three rounds, and their late rounds each found one
inaccurate sentence in a comment. Most tasks passed first time, and few reach the cap. The cap
does not claim late rounds are worthless. It hands the call to the user rather than declaring
the change done.

**One round for an analysis.** A written analysis informs a decision and changes nothing an
agent runs. Grading it catches real errors that would mislead the decision. But in the case
that prompted this rule, re-grading was not what found them: each later round was a fresh
sample that found different things, including an error present since the first draft that two
graders had already read past. One round buys most of the value. So an analysis gets one full
grade, then every problem it reports is fixed in place and listed where a reviewer will see it.
