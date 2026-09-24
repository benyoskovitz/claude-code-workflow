#!/usr/bin/env bash
# ff-sync-branch.sh — bring a repo's local sync branch back in line with origin.
#
# Usage: ff-sync-branch.sh <repo-path> <branch> [quiet-skip]
# Prints a short status, usually one line. Never fails the caller: always exits 0.
# `quiet-skip` suppresses the "uncommitted changes" line only, for a caller that
# already warns about a dirty repo itself.
#
# Two cases, one of which the old inline copies of this logic got wrong.
#
#   Behind only            → fast-forward. Always was handled.
#   Ahead, content upstream → RESET. The case the old inline copies missed.
#                            A commit made on the local sync branch and then
#                            pushed through a squash-merged PR lands upstream
#                            under a different sha. Git compares shas, so the
#                            local branch reads as "1 commit not on origin"
#                            forever and can never fast-forward again, and
#                            each new one adds to the pile until someone
#                            clears it by hand. `git cherry` compares patch-ids
#                            (content), so it can tell this apart from real
#                            unpushed work.
#   Ahead, content NOT upstream → skip and say so. Real work; never touched.


set -u

REPO="${1:-}"
BRANCH="${2:-}"
QUIET_SKIP="${3:-}"
[ -n "$REPO" ] && [ -n "$BRANCH" ] || { echo "usage: ff-sync-branch.sh <repo-path> <branch>" >&2; exit 0; }
[ -d "$REPO" ] || exit 0

g() { git -C "$REPO" "$@"; }

g rev-parse --git-dir >/dev/null 2>&1 || exit 0
g show-ref --verify -q "refs/heads/$BRANCH" || exit 0

# Never move a ref out from under uncommitted tracked work.
if ! g diff --quiet 2>/dev/null || ! g diff --staged --quiet 2>/dev/null; then
  [ -n "$QUIET_SKIP" ] || echo "$BRANCH sync skipped: uncommitted changes in $REPO"
  exit 0
fi

# Never move a ref out from under a LINKED worktree either. The repo's own HEAD
# cannot see them, so `symbolic-ref HEAD` below would report the branch as not
# checked out and take the `update-ref` arm — which moves the ref while another
# worktree's index still describes the old tree, staging a phantom deletion of
# every file the move drops. `git worktree list --porcelain` is the only view
# that covers all of them.
SELF=$(g rev-parse --show-toplevel 2>/dev/null || echo "")
OTHER_WT=""
_wt=""
while IFS= read -r _line; do
  case "$_line" in
    "worktree "*) _wt="${_line#worktree }" ;;
    "branch refs/heads/$BRANCH") [ "$_wt" = "$SELF" ] || OTHER_WT="$_wt" ;;
  esac
done <<EOF
$(g worktree list --porcelain 2>/dev/null)
EOF
if [ -n "$OTHER_WT" ]; then
  echo "$BRANCH sync skipped: checked out in another worktree ($OTHER_WT)"
  exit 0
fi

g fetch -q origin "$BRANCH" 2>/dev/null || true
g show-ref --verify -q "refs/remotes/origin/$BRANCH" || exit 0

AHEAD=$(g rev-list --count "origin/$BRANCH..$BRANCH" 2>/dev/null || echo 0)
BEHIND=$(g rev-list --count "$BRANCH..origin/$BRANCH" 2>/dev/null || echo 0)
AHEAD=${AHEAD:-0}; BEHIND=${BEHIND:-0}

[ "$AHEAD" -eq 0 ] && [ "$BEHIND" -eq 0 ] && exit 0

HEAD_REF=$(g symbolic-ref --quiet --short HEAD 2>/dev/null || echo "")

if [ "$AHEAD" -gt 0 ]; then
  # `git cherry <upstream> <head>` prints "+ <sha>" for each commit whose patch
  # is NOT upstream and "- <sha>" for each one that already is. Anything with a
  # "+" is real work: stop, exactly as before.
  UNIQUE=$(g cherry "origin/$BRANCH" "$BRANCH" 2>/dev/null | awk '$1 == "+" {print $2}')
  if [ -n "$UNIQUE" ]; then
    echo "$BRANCH sync skipped: $(printf '%s\n' "$UNIQUE" | grep -c .) commit(s) not on origin/$BRANCH"
    exit 0
  fi

  # Every commit ahead is already upstream under a different sha. Resetting
  # discards no COMMITTED content. The dropped shas are printed and stay in the
  # reflog.
  DROPPED=$(g rev-list "origin/$BRANCH..$BRANCH" 2>/dev/null | cut -c1-8 | tr '\n' ' ')
  if [ "$HEAD_REF" = "$BRANCH" ]; then
    # UNTRACKED content is the one thing the reflog cannot return, because git
    # was never given a copy. `reset --hard` leaves untracked files alone except
    # where the target commit tracks a path of the same name — there it
    # overwrites, silently. The fast-forward arm below never reaches this state
    # (`merge --ff-only` refuses on its own), so the guard belongs here alone.
    COLLIDE=""
    while IFS= read -r f; do
      [ -n "$f" ] || continue
      g cat-file -e "origin/$BRANCH:$f" 2>/dev/null && COLLIDE="$COLLIDE $f"
    done <<EOF
$(g ls-files --others --exclude-standard 2>/dev/null)
EOF
    if [ -n "$COLLIDE" ]; then
      echo "$BRANCH sync skipped: reset would overwrite untracked file(s) origin/$BRANCH also tracks:$COLLIDE"
      echo "  Commit, move, or delete them, then run this again."
      exit 0
    fi
    g reset --hard -q "origin/$BRANCH" 2>/dev/null || { echo "$BRANCH sync failed: reset --hard rejected"; exit 0; }
  else
    g update-ref "refs/heads/$BRANCH" "origin/$BRANCH" 2>/dev/null || { echo "$BRANCH sync failed: update-ref rejected"; exit 0; }
  fi
  echo "$BRANCH re-synced to origin/$BRANCH — dropped ${DROPPED% } (already upstream under a different sha; in the reflog)"
  exit 0
fi

# Behind only: plain fast-forward.
if [ "$HEAD_REF" = "$BRANCH" ]; then
  g merge --ff-only -q "origin/$BRANCH" 2>/dev/null || { echo "$BRANCH sync failed: ff-only merge rejected"; exit 0; }
else
  g update-ref "refs/heads/$BRANCH" "origin/$BRANCH" 2>/dev/null || { echo "$BRANCH sync failed: update-ref rejected"; exit 0; }
fi
echo "Local $BRANCH fast-forwarded to origin/$BRANCH ($BEHIND commits)."
exit 0
