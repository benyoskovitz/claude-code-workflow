End-of-session handoff. Produce a concise summary of this session, commit it, and clean up the worktree. Work through the steps below in order.

This is the **deterministic hot path**: notes → commit → push → cleanup. Two related commands are split out so cleanup is never blocked by other work:

- `/session-audit`: review CLAUDE.md and memory files for stale rules, undocumented workarounds, contradictions. Run on its own cadence (weekly, after a long arc, or when something feels off).
- `/worktree-janitor`: sweep the project's `.claude/worktrees/` directory and clean up orphans, phantoms, and stale worktrees from prior sessions. Run when the worktree directory feels cluttered.

> Customize before use: the commit footer below uses a generic Co-Authored-By line, and the push logic detects a "staging-first" project. If your default branch is `main` and you don't use a staging branch, the push step falls through to the branch's upstream automatically, no change needed.

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

This pairs with a `SessionStart` hook that reads the most recent few files back into context. See `hooks/settings.json`. Without that hook the notes are write-only and nobody reads them.

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

Push to the right ref:

- **Staging-first project** (search project CLAUDE.md for `staging-first` / `push to staging` / a rule naming `origin/staging` as the working branch): `git push origin HEAD:staging`, then handle the two ways it can fail, below.
- **Otherwise:** `git push` (branch upstream).
- **No remote:** leave the commit local; tell the user to push manually when ready.

### When the staging push is rejected

A direct push to a shared branch fails in two different ways, and they need different fixes. Read the push's error output before reacting.

**"protected branch" or "refusing to allow" (a branch protection rule requires a pull request).** Don't retry the direct push, it will never succeed. Route the same commit through a throwaway branch and a PR instead:

```bash
git push origin HEAD:refs/heads/session-notes/$(date +%Y%m%d-%H%M%S)
```

Then open a pull request into `staging` and let it merge itself once checks pass:

```bash
gh pr create --base staging --title "docs: session notes" --body "Automated session-notes commit from /session-end." --head <the-branch-you-just-pushed>
gh pr merge --auto --merge <pr-number>
```

Use `--merge`, **not** `--squash`. Step 7's cleanup gate only removes the worktree once this exact commit is reachable from a remote ref. A merge commit keeps that SHA on `staging`; a squash rewrites it into a new commit and the gate will correctly refuse to clean up. If auto-merge is disabled on the repo, leave the PR open and tell the user it needs a manual merge.

**"non-fast-forward" (someone else pushed first).** Replay only your notes commit onto the updated branch and try once more:

```bash
git fetch origin staging
git rebase --onto origin/staging HEAD~1 HEAD
git push origin HEAD:staging
```

If it's rejected a second time, stop and tell the user rather than looping.

## 5. Confirm

Tell the user what was written, where it was committed, and which ref it was pushed to. Flag anything ambiguous (e.g. unsure whether something is "completed" vs "in progress").

## 6. Fast-forward main repo's local default branch (worktree sessions only)

If the working directory is inside a worktree (path contains `/.claude/worktrees/`) AND the project is staging-first, update the main repo's local `staging` to match `origin/staging`, so the next worktree cut from `staging` starts fresh. Run BEFORE step 7 (removal destroys this shell).

```bash
MAIN_REPO=$(echo "$PWD" | sed 's|/\.claude/worktrees/.*||')
if ! git -C "$MAIN_REPO" diff --quiet || ! git -C "$MAIN_REPO" diff --staged --quiet; then
  echo "Skipping main-repo update: uncommitted changes in main repo."
else
  git -C "$MAIN_REPO" fetch --quiet origin staging
  AHEAD=$(git -C "$MAIN_REPO" rev-list --count origin/staging..staging 2>/dev/null || echo 0)
  if [ "$AHEAD" -gt 0 ]; then
    echo "Skipping: local staging has $AHEAD commit(s) not on origin, push first."
  else
    MAIN_HEAD=$(git -C "$MAIN_REPO" rev-parse --abbrev-ref HEAD)
    if [ "$MAIN_HEAD" = "staging" ]; then
      git -C "$MAIN_REPO" merge --ff-only origin/staging
    else
      git -C "$MAIN_REPO" update-ref refs/heads/staging origin/staging
    fi
    echo "Main-repo local staging fast-forwarded to origin/staging."
  fi
fi
```

**Why this exists:** worktrees push to `origin/staging` via PRs, but those commits never flow back into the main repo's local `staging` unless someone manually pulls. Without this, local `staging` drifts behind, and any new worktree cut from it starts stale. This closes the loop. Skip silently if not in a worktree or the project has no `staging` branch.

## 7. Worktree cleanup (if applicable)

If inside a worktree (path contains `/.claude/worktrees/`), check whether it's safe to remove. This must be the **last** operation, removing the worktree destroys the working directory, so no tool call can run after it.

**Safety gates, both must pass:**

1. **Tree clean** (same check as step 2): `git diff --quiet && git diff --staged --quiet`
2. **HEAD is durable on a remote ref:**
   ```bash
   git fetch --quiet origin
   git branch -r --contains HEAD | head -1
   ```
   At least one remote branch must contain HEAD (it may be on `origin/staging` awaiting a PR, that counts; durability ≠ deployed).

**If both pass:** classify untracked files (allowlist = local IDE/session state, expected to be lost). Ask **once**, with full disclosure of any non-allowlisted files that removal would discard. Wait for explicit confirmation. Then derive the main repo path by stripping `/.claude/worktrees/<name>`, and run:

```bash
git -C <main_repo_path> worktree remove --force <worktree_path>
```

(`--force` is needed because plain `remove` refuses on any untracked file, including allowlisted ones, the file-loss decision was already made above.) Report the result and stop. Do not issue further tool calls.

**If either gate fails, skip cleanup** and say why in one line (dirty tree, or commit not on a remote yet → push and re-run). **If not in a worktree:** skip silently.
