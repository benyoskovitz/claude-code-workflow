# workflow-meta

A cross-project lab for improving how you work with Claude Code. Ideas live here before they graduate into `~/.claude/` or a per-project CLAUDE.md.

The point: your runtime config (`~/.claude/`) should hold only adopted, working rules. Half-finished ideas, comparisons against external frameworks, and post-mortems don't belong there. They'd bloat every session. They belong here, where they're reflective rather than loaded.

## Layout

- `analyses/` holds write-ups comparing your current workflow against an external article, tool, or framework. Dated filenames: `YYYY-MM-DD-topic.md`.
- `proposals/` holds concrete proposed changes (a new skill, a CLAUDE.md section, a hook) before adoption. Each references the analysis that motivated it. Numbered: `NNN-name.md`.
- `adrs/` holds Architectural Decision Records for *workflow* decisions ("why path-scoped rules over per-project copies"). Numbered: `NNN-short-title.md`.

## Worked example

The `EXAMPLE-*` files show a full lifecycle so you don't have to guess what a real entry looks like: an analysis (`analyses/EXAMPLE-2026-02-10-plan-before-coding.md`), the proposal it motivated (`proposals/EXAMPLE-001-investigation-report-rule.md`), and the ADR that recorded the decision (`adrs/EXAMPLE-001-plan-before-nontrivial-changes.md`). Delete them once you've got the hang of it. The `TEMPLATE.md` in each folder is the blank you start from.

## Lifecycle

1. A new idea or external article becomes `analyses/YYYY-MM-DD-topic.md`.
2. If the analysis surfaces something worth adopting, write `proposals/NNN-name.md` with the *exact* change (the CLAUDE.md diff, the skill content, the hook script).
3. If adopted, the change lands in `~/.claude/` or a project, and the proposal gets an `# Adopted YYYY-MM-DD` header plus a link to the commit.
4. If rejected, the proposal stays for the record with a `# Rejected YYYY-MM-DD` header plus the reasoning. Rejected proposals are as valuable as adopted ones. They stop you re-litigating the same idea in six months.

## Why this isn't in `~/.claude/`

`~/.claude/` is *runtime* config, read on every session. This lab is *reflective*: hypotheses, comparisons, post-mortems. Keeping them separate prevents runtime config from filling up with ideas the agent has to load but shouldn't act on.

## Discipline that makes it work

- **Verify external claims before adopting them.** Articles about Claude Code config cite specific numbers that are often wrong. Check them against Anthropic's actual docs before you build on them. (A real example: a popular article claimed hard 6K/12K-character caps on rule files. Those don't exist. The real number is a roughly 200-line soft target, and it applies to a different file. The article's *direction* was right; its *facts* weren't.)
- **Two-doc minimum for any real change:** the analysis (why) and the proposal (exactly what). The proposal includes non-goals and alternatives-considered, so future-you knows what was deliberately left out.
- **Observation windows.** When you adopt something, set a date to review whether it actually helped. Keep, tune, or roll back on evidence, not vibes.
