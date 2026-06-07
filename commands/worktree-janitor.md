Audit and clean up Claude Code worktrees in the current project. Lists every worktree with status, classifies orphans and phantom registrations, and prompts per-worktree to keep or remove.

Use this any time the worktree directory feels cluttered, or when `/session-end` left debris behind. Safe to run on a project that doesn't use worktrees, it reports cleanly and exits.

> Assumes the convention of placing worktrees under `<repo>/.claude/worktrees/<name>` and a default integration branch (this command defaults to `origin/staging`, falling back to `origin/main`). Adjust both to your setup.

## 1. Locate the main repo

If `$PWD` contains `/.claude/worktrees/`, strip everything from that segment on. Otherwise use `git rev-parse --show-toplevel`.

```bash
if echo "$PWD" | grep -q '/\.claude/worktrees/'; then
  MAIN_REPO=$(echo "$PWD" | sed 's|/\.claude/worktrees/.*||')
else
  MAIN_REPO=$(git rev-parse --show-toplevel 2>/dev/null)
fi
[ -z "$MAIN_REPO" ] || [ ! -d "$MAIN_REPO/.git" ] && { echo "Not in a git repo. Nothing to do."; exit 0; }
```

If `$MAIN_REPO/.claude/worktrees/` doesn't exist, say "No worktrees directory found, nothing to clean" and stop.

## 2. Prune phantom git registrations

A phantom is a worktree git knows about whose directory was deleted manually. `git worktree prune` removes these safely.

```bash
git -C "$MAIN_REPO" worktree prune --verbose
```

Report what was pruned (or "none").

## 3. Build the audit table

Fetch first so the integration branch reflects truth: `git -C "$MAIN_REPO" fetch --quiet origin`. For each subdirectory of `.claude/worktrees/` AND each `git worktree list` entry, gather: `name`, `on_disk`, `in_git`, `branch`, `ahead`/`behind` (vs `origin/staging` or `origin/main`), `dirty_tracked` count, `untracked_real` (untracked files NOT on the local-state allowlist: `.claude/settings.local*.json`, `*.tmp`, `.DS_Store`, `Thumbs.db`), `on_remote` (`git branch -r --contains HEAD | head -1`), `last_activity` (`git log -1 --format=%cr`), and `heartbeat_age` (seconds since `<wt>/.claude/.in-use` was last touched, or null).

## 4. Classify each worktree

First match wins:

| Class | Condition | Default action |
|---|---|---|
| **ORPHAN** | on_disk but NOT in_git, or missing/broken `.git` | `rm -rf` dir |
| **EMPTY** | on_disk, no real contents | `rm -rf` dir |
| **CURRENT** | path matches `$PWD` | skip, your live session |
| **LIVE** | not `$PWD` but `heartbeat_age` fresh (< staleness threshold, default 2h) | skip, another live session |
| **SAFE** | clean, no untracked-real, on a remote, in_git, no live heartbeat | `git worktree remove` |
| **DIRTY** | dirty_tracked > 0 or untracked_real non-empty | prompt, show files |
| **LOCAL-ONLY** | clean but not on any remote | prompt, show ahead count |
| **STALE** | last_activity > 14 days, other gates pass | surface; default remove |

**Why LIVE matters:** with multiple Claude Code sessions open in parallel, each writes a heartbeat to its own worktree's `.claude/.in-use` (refreshed by global hooks on SessionStart / UserPromptSubmit / Stop). The janitor must NOT remove a worktree another session is using, that would yank the working directory out from under it mid-message. The heartbeat is the cross-session liveness signal.

Print the table to the user, grouped by class, before any action.

## 5. Confirm and act

Group prompts by safety tier, don't ask 8 separate questions.

- **Tier A, SAFE + EMPTY + STALE + ORPHAN.** One prompt: "Remove the N worktrees above?" On yes, loop: SAFE uses `git -C "$MAIN_REPO" worktree remove --force <path>`; ORPHAN/EMPTY use `rm -rf <path>` then `git worktree prune`. Never include CURRENT or LIVE.
- **Tier B, DIRTY.** One at a time: show the dirty/untracked files, ask keep / discard / inspect. Default keep. Never `--force` without per-worktree confirmation.
- **Tier C, LOCAL-ONLY.** One at a time: show ahead count + last commit subject, ask push / keep / discard. If push, `git -C <wt> push -u origin HEAD`, then re-classify.

## 6. Report

Print final state: removed, kept, remaining. Re-run `git worktree list` to confirm the registry matches reality. Name any kept DIRTY/LOCAL-ONLY worktrees and why.

## Safety rules

- **Never** `rm -rf` a path unless it ends in `<name>/` under `.claude/worktrees/`.
- **Never** remove the current worktree (matching `$PWD`).
- **Never** delete a worktree with commits not on any remote without explicit confirmation including the ahead count.
- **Always** `git worktree prune` after a manual `rm -rf`.
- If anything fails (e.g. a lock), report and skip, do not retry with escalating force.
