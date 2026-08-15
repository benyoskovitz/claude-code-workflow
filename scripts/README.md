# Scripts, the checks that are cheaper to run than to remember

Two things belong in a script rather than in a rule: anything with real logic, and anything you want to run on demand without an agent in the loop. Everything here is read-only and needs no network.

## Files

- `supply-chain-scan.sh`: sweeps a repo for two specific compromise signals. Pure grep and bash, no dependencies. Run it against any checkout: `bash scripts/supply-chain-scan.sh /path/to/repo`. Exits 0 when clean, 1 on findings.

## What the scan looks for

**A whitespace-injector signature (critical).** A run of 200 or more blank characters followed by code, in any tracked `.js`, `.mjs`, `.cjs`, `.ts`, or `.tsx` file. This is the tell for a class of attack that hides a payload inside a config file by pushing it far off the right edge of the screen, where nobody scrolls. A hit here is not a style problem. Stop, don't build or commit, and treat the machine as compromised.

**Unpinned `npx ...@latest` (warning).** In `package.json` and MCP config files. `@latest` re-resolves on every single run, so a package that was safe yesterday can be replaced upstream and execute on your machine today without anything in your repo changing. Pin to an exact version.

## Why a script and not a rule

A CLAUDE.md rule saying "watch for supply-chain risks" is unenforceable, and an agent reading a compromised file is exactly the moment it can't be trusted to notice. This runs the same way every time, in a second, whether or not an agent is involved.

Pair it with the `/pre-commit` skill, which carries the `@latest` rule as a warn-level check on staged diffs. The skill catches new occurrences as you write them; this script sweeps everything already in the tree.
