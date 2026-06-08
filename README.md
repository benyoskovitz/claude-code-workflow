# A Claude Code workflow that improves itself

This is the companion repo to my Focused Chaos post, [How I Ship Real Software with Claude Code (without being a developer)](https://focusedchaos.co/how-i-ship-real-software-with-claude-code). It's not a dump of my config. It's the reusable parts, sanitized and templated, so you can fork what's useful and leave the rest.

A note on what this is and isn't. It isn't a comprehensive toolkit, and it isn't trying to be. If you want a full pre-built engineering team in a box, Garry Tan's [gstack](https://github.com/garrytan/gstack) is bigger and more complete. This is smaller and more opinionated. It's the handful of habits that made AI-written code trustworthy for me, plus the structure I use to keep improving them. The value is in the discipline, not the number of tools.

The most useful thing here isn't any single file. It's the loop: define what "done" means before the agent writes code, grade the result against that definition, and treat the workflow itself as something you version and improve over time.

## What's in here

| Folder | What it is | Priority |
|---|---|---|
| `CLAUDE.md.template` | Annotated skeleton for a project memory file, with the universal parts filled in and the project-specific parts marked as placeholders | High. Start here |
| `skills/assess/` | The `/assess` skill: grades a diff against a task rubric, refuses to proceed on a fail | High. The centerpiece |
| `rules/` | Path-scoped rules pattern: keep CLAUDE.md lean by loading stack-specific guidance only when relevant files are read | High |
| `workflow-meta/` | The "lab" for versioning your workflow: analyses, proposals, and ADRs, with one worked example | High. The most distinctive idea here |
| `skills/pre-commit/` | A genericized commit gate (secrets, missing auth, anti-patterns). A scaffold to adapt, not a finished tool | Medium. Fill in your own rules |
| `skills/code-watch/` | Deep, on-demand two-lens audit: security/bugs plus conformance to your CLAUDE.md's own rules. Runs inline, no setup. Overlaps Claude Code's built-in `/security-review` | Medium |
| `hooks/` | Guardrail hooks: nudge the commit skill, inject reminders, flag risky edits. Mechanism is generic, contents are yours | Medium |
| `commands/` | Session lifecycle and upkeep. `/blast-radius` and the audit commands are broadly useful; `/session-end` and `/worktree-janitor` assume a git-worktree plus staging-first workflow and are advanced | Mixed. Read before adopting |
| `examples/` | Filled-in sample artifacts (rubric, investigation report, quality rules) so you can see the shapes | Reference |

## The core idea: define "done" before Execute

Most agent frustration comes from the model declaring victory early. It does *something*, says it's finished, and you find out later it missed half the point. The fix isn't a better prompt. It's a contract written before the work starts.

The loop:

1. **Plan.** For any non-trivial change, produce an Investigation Report (see `CLAUDE.md.template`) or use Plan Mode. The last section is a **task rubric**: 3 to 5 mutually-exclusive pillars, each with a binary pass criterion. Write it to `.rubric.md` at the repo root.
2. **Execute.** Do the work.
3. **Assess.** Run `/assess`. It reads `.rubric.md`, runs `git diff`, and grades each pillar pass or fail with cited evidence. Pass means it archives the rubric and clears you for commit. Fail means it stops and outputs a re-plan directive. It does not patch in place, and it does not invent a rubric if you didn't write one.
4. **Pre-commit.** Run `/pre-commit`, a fast anti-pattern and secret scan on every commit.
5. **Commit.**

For changes that touch sensitive surfaces (auth, queries, uploads, crypto), there's a heavier optional pass. `/code-watch` runs a deeper security and quality audit on demand. The three verification skills do different jobs and shouldn't be collapsed. `/pre-commit` checks *the global don't-ship-this rules* (fast, every commit). `/code-watch` is *the deep audit before a risky merge* (slow, on demand). `/assess` checks *did this change do what the task required* (per-task contract). Cheap and frequent at the bottom, thorough and occasional at the top.

Three deliberate non-goals keep `/assess` honest:

- **No 1-to-10 scoring.** Binary per pillar. Numeric scores invite self-debate and fake precision.
- **No automatic re-plan execution.** `/assess` reports and stops. You drive the re-plan. Autonomous re-planning on a misspecified rubric is how agents run away.
- **No rubric inference.** No `.rubric.md`, no assessment. Inferring the contract after the fact defeats the purpose.

## The second idea: a CLAUDE.md that earns its lines

Anthropic's soft target is under 200 lines, because longer files reduce adherence. The litmus test (borrowed from Yanli Liu's writing on the subject, then verified against Anthropic's own docs):

> Does this shape how the agent *thinks*, or just tell it what to *do*?

"How it thinks" (behavioral principles, security posture, your workflow loop) stays in CLAUDE.md and loads every session. "What it does" (stack-specific tactical patterns) moves to `rules/` files with `paths:` frontmatter, so they only load when the agent reads a matching file. See `rules/README.md`.

Claude Code reads two CLAUDE.md files at session start: a global one at `~/.claude/CLAUDE.md` (cross-project behavior, loads everywhere) and a per-project one at the repo root (project-specific machinery). The `CLAUDE.md.template` here bundles both layers into one file so you can start simple; its top comment explains how to split them if you want the two-file setup.

## The third idea: version your workflow, not just your code

`workflow-meta/` is a separate lab where workflow changes get proposed, argued, adopted, or rejected before they touch your runtime config. A new idea or external article goes in `analyses/`. A concrete proposed change goes in `proposals/`. A decision with lasting consequences gets an `adrs/` record. This keeps your live config clean (it only holds adopted, working rules) and gives you a paper trail for *why* each rule exists. That matters, because the best rules are usually scars from a specific incident. There's a worked example in `workflow-meta/` (an analysis, the proposal it motivated, and the ADR that recorded the decision) so you can see a full lifecycle, not just blank templates.

## The fourth idea: commands for the session lifecycle

Skills do the work; commands manage the work around it. The `commands/` folder holds the lifecycle and upkeep pieces:

- **`/blast-radius`** greps the real importers, callers, and tests of a file or symbol before a change, so the Investigation Report is grounded in fact. Useful in any repo.
- **`/audit-instructions`** grades your instruction files against eight failure modes (vague scope, no verification step, duplicate source of truth, and so on) and tightens the loose ones.
- **`/project-health`** audits a project's whole Claude setup (CLAUDE.md completeness, command and hook coverage, outstanding debt) and reports prioritized gaps.
- **`/session-audit`** periodically re-reads your CLAUDE.md and memory for stale rules, undocumented workarounds, and contradictions with the actual code.
- **`/session-end`** is the deterministic wrap-up: it writes structured session notes, commits and pushes them, and safely cleans up the git worktree only once your work is provably saved.
- **`/worktree-janitor`** sweeps stale, orphaned, and phantom git worktrees, with a heartbeat check so it never deletes one a parallel session is actively using.

The last two assume git worktrees under `<repo>/.claude/worktrees/` and (optionally) a staging-first branch model. Both are noted inline and degrade gracefully if your setup differs, but if you don't use worktrees, most of their value won't apply to you.

## How to use this repo

1. Copy `CLAUDE.md.template` to your project as `CLAUDE.md` and fill in the placeholders.
2. Copy `skills/` into `~/.claude/skills/` (user scope) or `./.claude/skills/` (project scope).
3. Copy `commands/` into `~/.claude/commands/` (user scope) or `./.claude/commands/` (project scope).
4. Copy `rules/` into `~/.claude/rules/` and adjust the `paths:` globs to your stack.
5. Copy `hooks/settings.json` into `.claude/settings.json` and adapt the trigger contents.
6. Start a `workflow-meta` repo of your own. Don't put it inside any project.

One caveat, and I mean it. Don't copy all of this in blindly. That's the opposite of the point. Read each piece, take the one or two ideas that fit how you work, and rebuild them so you understand them. The understanding is the asset, not the config file.

Everything here is MIT licensed.

## Credits and inspiration

The skills, commands, and templates here are my own work and wording. A few of the *ideas* came from elsewhere, and credit is due.

The task-rubric and `/assess` loop was inspired by **SPEAR** (Scope, Plan, Execute, Assess, Resolve), written up here: [introducing SPEAR](https://www.edge.ceo/p/introducing-spear-the-management). I adopted the "define a scored contract before you build" idea and deliberately changed it: binary pillars instead of 1-to-10 scoring, and no autonomous re-planning.

The Behavioral Principles block and the lean, path-scoped CLAUDE.md approach were shaped by Yanli Liu's *"The 4 Lines Every CLAUDE.md Needs"* (Level Up Coding, 2026) and the [Karpathy CLAUDE.md thread](https://x.com/karpathy/status/2015883857489522876). Worth noting: I fact-checked the article's specific claims against Anthropic's docs and several didn't hold up (the "6K/12K character caps" don't exist; the real guidance is a roughly 200-line soft target). The directional argument is sound; the specifics aren't. Verify before you adopt.

Implementations and all wording are mine. These are the conceptual lineages, not sources I copied.
