End-of-session handoff. Produce a concise summary of this session, commit it, and clean up the worktree. Work through the steps below in order.

This is the **deterministic hot path**: notes → commit → push → cleanup. Two related commands are split out so cleanup is never blocked by other work:

- `/session-audit`: review CLAUDE.md and memory files for stale rules, undocumented workarounds, contradictions. Run on its own cadence (weekly, after a long arc, or when something feels off).
- `/worktree-janitor`: sweep the project's `.claude/worktrees/` directory and clean up orphans, phantoms, and stale worktrees from prior sessions. Run when the worktree directory feels cluttered.

> Customize before use: the commit footer below uses a generic Co-Authored-By line, and the push logic detects a "staging-first" project. If your default branch is `main` and you don't use a staging branch, the push step pushes the session's own branch instead, no change needed.

## 1. Gather context

Review the conversation history from this session. Identify:

- **Completed work**: what was built, fixed, refactored, or decided
- **In-progress work**: anything started but not finished, and its current state
- **Next steps**: what logically comes next
- **Decisions made**: architectural choices, trade-offs, scope decisions, and the reasoning
- **Blockers / open questions**: anything unresolved the next session needs to address

## 2. Pre-flight: tree-state gate

Before writing anything, check the tree has no pre-existing unfinished code work, otherwise the session-notes commit will bury it.

```bash
git diff --quiet && git diff --staged --quiet
```

This ignores untracked files (local IDE state, lock files). It only fails on modifications to tracked files or staged changes.

Also record the branch you are on, because step 4 can leave you on a bare commit and must put you back:

```bash
git branch --show-current
```

Write the name it prints into later commands in place of `<SESSION_BRANCH>`. If it prints nothing, you are on a bare commit (detached `HEAD`), and there is no branch to push to or return to. **STOP** and tell the user: "Not on a branch. Check out or create one, then re-run /session-end."

**If the check fails:** run `git status --short | grep -v '^??'` to list the unfinished changes, then **STOP** and tell the user: "Uncommitted code work present, commit, stash, or discard before /session-end so the session-notes commit doesn't bury it."

**If untracked files exist beyond a local-state allowlist** (`.claude/settings.local*.json`, `*.tmp`, `.DS_Store`): list them and ask "Untracked files present, they'll be lost when the worktree is removed. Proceed?" Wait for confirmation.

**If not in a git repo:** skip steps 4, 6, and 7. Just write notes (step 3) and report (step 5).

## 3. Write the session-notes file

Write **one new file per session** into `session-notes/`, never a shared file that every session appends to:

```bash
mkdir -p session-notes
date "+%Y-%m-%d-%H%M"
```

The path is `session-notes/<timestamp>-<short-slug>.md`, where the slug is two or three words describing the session (`worktree-cleanup`, `auth-redirect-fix`). Use the **Write tool**: the file never exists yet, so there is nothing to append to or trim.

**Why one file per session, not one shared file.** Two sessions running in parallel worktrees can never write the same path, so they can never conflict. A single shared notes file guarantees a merge conflict the moment two sessions finish close together, and that conflict lands in the one file whose whole job is to be readable at the start of the next session. If your project already has a `SESSION_NOTES.md` from an older setup, leave it alone as a frozen archive and start the directory alongside it.

This pairs with a `SessionStart` hook, `hooks/session-start-notes.sh`, that reads the `Next Steps` and `Blockers / Open Questions` sections of the last two files back into context. Keep those two headings exactly as below: the hook finds them by name. Put anything the next session must act on under one of them, because the other sections are not read back. Without that hook the notes are write-only and nobody reads them.

Format:

```markdown
## Session, YYYY-MM-DD HH:MM

### Completed
- [what was done]

### In Progress
- [what's partially done and its state, or "None"]

### Next Steps
- [concrete next actions, ordered by priority]

### Decisions
- [decision]: [why]

### Blockers / Open Questions
- [blocker or question, or "None"]
```

Use the current date and time. One line per bullet. Be specific, reference file names, function names, feature names. This is for a developer picking up where you left off, not a stakeholder update.

## 4. Commit & push the session-notes change

Skip if not in a git repo, or if the notes path is gitignored (`git check-ignore <notes-file>` returns 0).

Stage **only** the one notes file by name (never `git add .` in a session that may have parallel work):

```bash
git add <notes-file>
```

Quick secret scan on the staged diff (markdown-only fast path, skip the full `/pre-commit` suite, since a docs-only change can't break build/tests):

```bash
git diff --staged | grep -E "^\+" | grep -iE "sk-[A-Za-z0-9]{20,}|key-[A-Za-z0-9]{20,}|postgres(ql)?://[^[:space:]]+:[^[:space:]]+@|aws_secret|password\s*=\s*['\"][^'\"]+" || true
```

If anything matches, **STOP**, show the user, and ask before committing.

Commit with a focused message:

```bash
git commit -m "$(cat <<'EOF'
docs: session notes, <one-line topic of this session>

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

The topic is a tight summary of step 1's "Completed."

Record the notes commit's sha the moment it exists, and use that sha, never `HEAD`, for every later push and check:

```bash
git rev-parse HEAD
```

Write the sha it prints into every later command below, in place of `<NOTES_SHA>`. Each command runs in a fresh shell, so a shell variable would not survive to step 7.

`HEAD` moves. A rebase below rewrites the commit, and a checkout or a parallel step can leave `HEAD` somewhere else. A durability check on `HEAD` can then pass while the notes commit itself is on no remote at all. If a rebase below rewrites the commit, re-record the sha straight after it.

Push to the right ref:

- **Staging-first project** (search project CLAUDE.md for `staging-first` / `push to staging` / a rule naming `origin/staging` as the working branch): replay only the notes commit onto a fresh `origin/staging`, then push it. The steps are in "Pushing to staging", below.
- **Otherwise:** push the branch by sha. This creates the remote branch when it is missing:
  ```bash
  git push origin <NOTES_SHA>:refs/heads/<SESSION_BRANCH>
  ```
  If it is rejected, stop and relay the error. Do not rebase and retry: on your own branch, a rejection means the remote holds work you have not seen, and that is the user's call.
- **No remote:** leave the commit local; tell the user to push manually when ready.

### Pushing to staging

Always replay only the notes commit. Pushing `<NOTES_SHA>` as it stands would also push every commit under it, and on a session branch those are the session's own unreviewed commits:

```bash
git fetch origin staging
git rebase --onto origin/staging <NOTES_SHA>~1 <NOTES_SHA>
git rev-parse HEAD
```

The rebase rewrites the commit, so it has a new sha. Record the one `git rev-parse HEAD` just printed as the new `<NOTES_SHA>`, and use it from here on, starting with the push:

```bash
git push origin <NOTES_SHA>:staging
```

The rebase also leaves `HEAD` detached (on a bare commit, not a branch). Once the push has landed, or failed for good, always return to the session's branch, in a worktree or not:

```bash
git checkout <SESSION_BRANCH>
```

Do it even when step 7 is about to remove the worktree. The user can decline the removal, and a gate can fail. Either way the worktree stays, and commits made later on a bare commit belong to no branch.

### When the staging push is rejected

A direct push to a shared branch fails in two different ways, and they need different fixes. Read the push's error output before reacting.

**"protected branch" or "refusing to allow" (a branch protection rule requires a pull request).** Don't retry the direct push, it will never succeed. Route the same commit through a throwaway branch and a PR instead:

```bash
git push origin <NOTES_SHA>:refs/heads/session-notes/$(date +%Y%m%d-%H%M%S)
```

Then open a pull request into `staging` and let it merge itself once checks pass:

```bash
gh pr create --base staging --title "docs: session notes" --body "Automated session-notes commit from /session-end." --head <the-branch-you-just-pushed>
gh pr merge --auto --merge <pr-number>
```

Prefer `--merge` to `--squash`. A merge keeps `<NOTES_SHA>` itself on `staging`, so the commit stays findable by its sha after the throwaway branch is deleted. Step 7 does not depend on the choice: it runs before any merge, and counts the throwaway branch as durable. If auto-merge is disabled on the repo, leave the PR open and tell the user it needs a manual merge.

If `gh pr create` itself fails, stop and lead your report with `NO PR OPENED`. The notes commit is on a remote branch, so nothing is lost, but nothing is queued for `staging` either. A person has to open that PR. Relay the error and the branch name.

**"non-fast-forward" (someone else pushed between your fetch and your push).** Run the three replay commands from "Pushing to staging" once more, record the new sha, and push again. If it's rejected a second time, stop and tell the user rather than looping.

## 5. Confirm

Tell the user what was written, where it was committed, and which ref it was pushed to. Flag anything ambiguous (e.g. unsure whether something is "completed" vs "in progress").

## 6. Re-sync the local staging branch (staging-first projects only)

If the project is staging-first, bring the local `staging` branch back in line with `origin/staging`, so the next worktree cut from it starts fresh. Run it against the main repo when inside a worktree (path contains `/.claude/worktrees/`), and against this repo otherwise. Run BEFORE step 7, because removal destroys this shell.

```bash
MAIN_REPO=$(echo "$PWD" | sed 's|/\.claude/worktrees/.*||')
bash ~/.claude/scripts/ff-sync-branch.sh "$MAIN_REPO" staging
```

Copy `scripts/ff-sync-branch.sh` from this repo to `~/.claude/scripts/` first. It prints a short status, usually one line. Relay it.

**Why a script and not a fast-forward.** Worktrees push to `origin/staging` via PRs, and those commits never flow back into the local `staging` unless someone pulls, so local `staging` drifts behind. A plain fast-forward fixes that, but misses a second case. A commit made on local `staging` and then shipped through a squash-merged PR lands upstream under a different sha. Git compares shas, so local `staging` reads as "1 commit ahead" forever and can never fast-forward again. The script uses `git cherry`, which compares content, to tell that apart from real unpushed work:

- **Behind only:** fast-forward.
- **Ahead, but every commit ahead is already upstream by content:** reset to `origin/staging`, and print the dropped shas (they stay in the reflog).
- **Ahead with real work:** leave it alone and say so.

It also refuses to move the branch when the repo has uncommitted changes, when another worktree has `staging` checked out, or when a reset would overwrite an untracked file. Skip this step silently if the project has no `staging` branch.

## 7. Worktree cleanup (if applicable)

If inside a worktree (path contains `/.claude/worktrees/`), check whether it's safe to remove. This must be the **last** operation, removing the worktree destroys the working directory, so no tool call can run after it.

**Safety gates, both must pass:**

1. **Tree clean** (same check as step 2): `git diff --quiet && git diff --staged --quiet`
2. **The notes commit is durable on a remote ref:**
   ```bash
   git fetch --quiet origin
   git branch -r --contains <NOTES_SHA> | head -1
   ```
   At least one remote branch must contain `<NOTES_SHA>` (it may be on a `session-notes/` branch awaiting its PR; that counts, because durable is not the same as deployed). If you no longer have the recorded sha, stop and say so rather than falling back to `HEAD`.

**If both pass:** classify untracked files (allowlist = local IDE/session state, expected to be lost). Ask **once**, with full disclosure of any non-allowlisted files that removal would discard. Wait for explicit confirmation. Then derive the main repo path by stripping `/.claude/worktrees/<name>`.

Before removing anything, decide whether the session's local branch can go too. Removal ends this shell, so this check has to come first. List the commits on the branch that no remote holds:

```bash
git cherry <NOTES_SHA> <SESSION_BRANCH> | sed -n 's/^+ //p' | while read c; do git branch -r --contains "$c" | grep -q . || echo "$c"; done
```

`git cherry` drops every commit whose content is already in `<NOTES_SHA>` or its history, under any sha. `<NOTES_SHA>` is the pushed notes commit, so that covers the session's original notes commit on every push path, and whatever the remote branch held when step 4 replayed onto it. The loop then drops every commit still on some remote branch by its own sha, such as work pushed to its own PR branch. What is left is on no remote by either test.

Then run exactly one of these two commands.

**Delete the branch too** only if the check printed nothing **and** `<SESSION_BRANCH>` is not `staging`, `main`, `master`, or the remote's default branch. Those are shared branches, not the session's own, even when the worktree was checked out on one. The deletion is chained onto the removal because nothing can run after it:

```bash
git -C <main_repo_path> worktree remove --force <worktree_path> && git -C <main_repo_path> branch -D <SESSION_BRANCH>
```

**Otherwise, remove only the worktree:**

```bash
git -C <main_repo_path> worktree remove --force <worktree_path>
```

If the check printed any sha, name those commits to the user and say the branch was kept. Say what the check can and cannot tell: no remote branch holds them, and the pushed notes commit's history does not match them by content. They may exist only on this machine. Or they shipped through a squash-merged PR whose branch was deleted, which changes both the sha and the content.

(`--force` is needed because plain `remove` refuses on any untracked file, including allowlisted ones, the file-loss decision was already made above.) Report the result and stop. Do not issue further tool calls.

**If either gate fails, skip cleanup** and say why in one line (dirty tree, or commit not on a remote yet → push and re-run). **Never tell the user the session is safe to archive unless gate 2 passed in this run.** A notes commit on no remote ref exists only on this machine, and removing the worktree or archiving the session is how it gets lost. **If not in a worktree:** skip silently.
