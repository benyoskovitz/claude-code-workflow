# Scripts, the checks that are cheaper to run than to remember

Two things belong in a script rather than in a rule: anything with real logic, and anything you want to run on demand without an agent in the loop. Everything here but `ff-sync-branch.sh` is read-only and needs no network. That one runs a `git fetch` and can move a branch ref.

## Files

Install: copy these into `~/.claude/scripts/`, which is where every command in this repo runs them from.


- `supply-chain-scan.sh`: sweeps a repo for two specific compromise signals. Pure grep and bash, no dependencies. Run it against any checkout: `bash ~/.claude/scripts/supply-chain-scan.sh /path/to/repo`. Exits 0 when clean, 1 on findings.
- `comment-claims.py`: lists the comment lines a change added that assert something about a whole ("every", "only", "exactly", "none"). Advisory: it always exits 0 on a scan. Run it in the project before `/assess`: `python3 ~/.claude/scripts/comment-claims.py`, or add `--base <ref>` when part of the work is already committed. Python 3, no dependencies.
- `ff-sync-branch.sh`: brings a local branch (usually `staging`) back in line with `origin`. Fast-forwards when behind. When ahead, resets only if every commit ahead is already upstream by content, which is what a squash-merged PR leaves behind, and leaves real unpushed work alone. `/session-end` step 6 calls it from `~/.claude/scripts/`: `bash ~/.claude/scripts/ff-sync-branch.sh <repo-path> staging`. It always exits 0 and prints a short status, usually one line.

## What the scan looks for

**A whitespace-injector signature (critical).** A run of 200 or more blank characters followed by code, in any tracked `.js`, `.mjs`, `.cjs`, `.ts`, or `.tsx` file. This is the tell for a class of attack that hides a payload inside a config file by pushing it far off the right edge of the screen, where nobody scrolls. A hit here is not a style problem. Stop, don't build or commit, and treat the machine as compromised.

**Unpinned `npx ...@latest` (warning).** In `package.json` and MCP config files. `@latest` re-resolves on every single run, so a package that was safe yesterday can be replaced upstream and execute on your machine today without anything in your repo changing. Pin to an exact version.

## What the comment checker is for

Comments are the one part of a change that nothing mechanical re-reads. The compiler, the linter and the tests all ignore them, so a false comment survives until a human or a grader reads it. In one measured stretch of real grading, about four in ten failing `/assess` rounds were blocked by prose alone, and most of the false sentences claimed more than the author had checked: "exactly two sites", "the only caller", "this list is the whole set".

`comment-claims.py` asks git which lines each changed file gained, works out which of those are comments, and prints the ones containing a word that claims a whole. Many hits are true sentences that simply use the word. That's why it's a re-read list rather than a gate: only the author can tell a true "every" from a false one. It pairs with the comment rule in `CLAUDE.md.template`, which says to write such a claim as the search that proves it rather than as a count.

Its blind spots are listed in its own header, and each one has a case in `--selftest`, so a blind spot that silently closes or opens shows up as a failing case:

```bash
python3 ~/.claude/scripts/comment-claims.py --selftest
```

A pass ends with `N of N cases behaved as documented.`

## Why the scan is a script and not a rule

A CLAUDE.md rule saying "watch for supply-chain risks" is unenforceable, and an agent reading a compromised file is exactly the moment it can't be trusted to notice. This runs the same way every time, in a second, whether or not an agent is involved.

Pair it with the `/pre-commit` skill, which carries the `@latest` rule as a warn-level check on staged diffs. The skill catches new occurrences as you write them; this script sweeps everything already in the tree.
