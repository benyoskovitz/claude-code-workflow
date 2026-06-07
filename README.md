# A Claude Code workflow that improves itself

This is the companion repo to my FocusedChaos post on how I work with Claude Code. It's not a dump of my config. It's the reusable parts, sanitized and templated, so you can fork what's useful and leave the rest.

The thing worth stealing here isn't any single file. It's the loop: define what "done" means before the agent writes code, grade the result against that definition, and treat the workflow itself as something you version and improve over time.

## What's in here

| Folder | What it is | Steal-ability |
|---|---|---|
| `CLAUDE.md.template` | Annotated skeleton for a project memory file, with the universal parts filled in and the project-specific parts marked as placeholders | High — start here |
| `skills/assess/` | The `/assess` skill: grades a diff against a task rubric, refuses to proceed on a fail | High — the centerpiece |
| `skills/pre-commit/` | Fast anti-pattern and secret scan on every commit | High — adapt the rules to your stack |
| `skills/code-watch/` | Deep, on-demand two-lens audit: security/bugs + conformance to your CLAUDE.md's own rules. Runs inline, no setup | High |
| `commands/` | Session lifecycle and upkeep: `/session-end`, `/session-audit`, `/worktree-janitor`, `/project-health`, `/audit-instructions`, `/blast-radius` | High |
| `rules/` | Path-scoped rules pattern: keep CLAUDE.md lean by loading stack-specific guidance only when relevant files are read | High |
| `hooks/` | Guardrail hooks: force the pre-commit skill, inject reminders, nudge on risky edits | Medium — mechanism is generic, contents are yours |
| `workflow-meta/` | The "lab" structure: analyses, proposals, and ADRs for the workflow itself | High — this is the unusual part |
| `examples/` | Redacted real artifacts so you can see what these look like in practice | Reference |

## The core idea: define "done" before Execute

Most agent frustration comes from the model declaring victory early. It does *something*, says it's finished, and you find out later it missed half the point. The fix isn't a better prompt — it's a contract written before the work starts.

The loop:

1. **Plan.** For any non-trivial change, produce an Investigation Report (see `CLAUDE.md.template`) or use Plan Mode. The last section is a **task rubric**: 3 to 5 mutually-exclusive pillars, each with a binary pass criterion. Write it to `.rubric.md` at the repo root.
2. **Execute.** Do the work.
3. **Assess.** Run `/assess`. It reads `.rubric.md`, runs `git diff`, and grades each pillar pass or fail with cited evidence. Pass means it archives the rubric and clears you for commit. Fail means it stops and outputs a re-plan directive. It does not patch in place, and it does not invent a rubric if you didn't write one.
4. **Pre-commit.** Run `/pre-commit` — a fast anti-pattern and secret scan on every commit.
5. **Commit.**

For changes that touch sensitive surfaces (auth, queries, uploads, crypto), there's a heavier optional pass: `/code-watch` runs a deeper security + quality audit on demand. The three verification skills do different jobs and shouldn't be collapsed: `/pre-commit` checks *the global don't-ship-this rules* (fast, every commit), `/code-watch` is *the deep audit before a risky merge* (slow, on demand), and `/assess` checks *did this change do what the task required* (per-task contract). Cheap and frequent at the bottom, thorough and occasional at the top.

Three deliberate non-goals keep `/assess` honest:

- **No 1-to-10 scoring.** Binary per pillar. Numeric scores invite self-debate and fake precision.
- **No automatic re-plan execution.** `/assess` reports and stops. You drive the re-plan. Autonomous re-planning on a misspecified rubric is how agents run away.
- **No rubric inference.** No `.rubric.md`, no assessment. Inferring the contract after the fact defeats the purpose.

## The second idea: a CLAUDE.md that earns its lines

Anthropic's soft target is under 200 lines, because longer files reduce adherence. The litmus test (borrowed from Yanli Liu's writing on the subject, then verified against Anthropic's own docs):

> Does this shape how the agent *thinks*, or just tell it what to *do*?

"How it thinks" — behavioral principles, security posture, your workflow loop — stays in CLAUDE.md and loads every session. "What it does" — stack-specific tactical patterns — moves to `rules/` files with `paths:` frontmatter, so they only load when the agent reads a matching file. See `rules/README.md`.

## The third idea: version your workflow, not just your code

`workflow-meta/` is a separate lab where workflow changes get proposed, argued, adopted, or rejected before they touch your runtime config. New idea or external article goes in `analyses/`. A concrete proposed change goes in `proposals/`. A decision with lasting consequences gets an `adrs/` record. This keeps your live config clean (it only holds adopted, working rules) and gives you a paper trail for *why* each rule exists — which matters, because the best rules are usually scars from a specific incident.

## The fourth idea: commands for the session lifecycle

Skills do the work; commands manage the work around it. The `commands/` folder holds the lifecycle and upkeep pieces:

- **`/session-end`** — the deterministic wrap-up: write structured session notes, commit and push them, then safely clean up the git worktree. It's the agent's memory handoff to the next session.
- **`/session-audit`** — periodically re-reads your CLAUDE.md and memory for stale rules, undocumented workarounds, and contradictions with the actual code. Keeps the ruleset honest.
- **`/worktree-janitor`** — sweeps stale, orphaned, and phantom git worktrees, with a heartbeat check so it never deletes one a parallel session is actively using.
- **`/project-health`** — audits a project's whole Claude setup (CLAUDE.md completeness, command/hook coverage, outstanding debt) and reports prioritized gaps.
- **`/audit-instructions`** — grades your instruction files against eight failure modes (vague scope, no verification step, duplicate source of truth, …) and tightens the loose ones.
- **`/blast-radius`** — before a change, greps the real importers, callers, and tests of a file or symbol, so the Investigation Report is grounded in fact.

The session-lifecycle ones assume the convention of git worktrees under `<repo>/.claude/worktrees/` and (optionally) a staging-first branch model; both are noted inline and degrade gracefully if your setup differs.

## How to use this repo

1. Copy `CLAUDE.md.template` to your project as `CLAUDE.md` and fill in the placeholders.
2. Copy `skills/` into `~/.claude/skills/` (user scope) or `./.claude/skills/` (project scope).
3. Copy `commands/` into `~/.claude/commands/` (user scope) or `./.claude/commands/` (project scope).
4. Copy `rules/` into `~/.claude/rules/` and adjust the `paths:` globs to your stack.
5. Copy `hooks/settings.json` into `.claude/settings.json` and adapt the trigger contents.
6. Start a `workflow-meta` repo of your own. Don't put it inside any project.

Everything here is MIT licensed. Fork it, gut it, make it yours.

## Credits & inspiration

The skills, commands, and templates here are my own work and wording. A few of the *ideas* came from elsewhere, and credit is due:

- **The task-rubric / `/assess` loop** was inspired by **SPEAR** (Scope · Plan · Execute · Assess · Resolve) — [introducing SPEAR](https://www.edge.ceo/p/introducing-spear-the-management). I adopted the "define a scored contract before you build" idea and deliberately changed it (binary pillars instead of 1-to-10 scoring, no autonomous re-planning).
- **The Behavioral Principles block** and the **lean, path-scoped CLAUDE.md** approach were shaped by Yanli Liu's *"The 4 Lines Every CLAUDE.md Needs"* (Level Up Coding, 2026) and the [Karpathy CLAUDE.md thread](https://x.com/karpathy/status/2015883857489522876). Worth noting: I fact-checked the article's specific claims against Anthropic's docs and several didn't hold up (the "6K/12K character caps" don't exist — the real guidance is a ~200-line soft target). The directional argument is sound; the specifics aren't. Verify before you adopt.

Implementations and all wording are mine; these are the conceptual lineages, not sources I copied.
