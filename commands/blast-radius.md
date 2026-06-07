---
description: Investigate the blast radius of a file or symbol, importers, direct callers, tests. Use before any non-trivial maintenance change.
---

Fills the Investigation Report's "Direct callers and importers" and "Tests covering this code path" sections (see `CLAUDE.md.template`) with real grep output, so the report is grounded in fact rather than a summary.

**Argument:** a file path (e.g. `src/lib/foo.ts`) or a symbol name (e.g. `generateThing`). Ask if missing.

Decide the arg type: it's a path if it contains `/` or ends in a source extension (`.ts`/`.tsx`/`.js`/`.jsx`/`.py`/`.go`/`.rs`/`.sql`...). Otherwise treat it as a symbol name. (The grep globs below assume a `src/` layout, adjust to your project's source root.)

**For a file path** (let `basename` = filename without extension):
- Importers: `git grep -nE "from ['\"][^'\"]*${basename}['\"]"` against the source root
- Tests: `git grep -lE "${basename}" -- '**/__tests__/**' '**/*.test.*'`

**For a symbol name** (`SYM`):
- All word-bounded references: `git grep -nw "${SYM}" -- src/`
  - Split the output: lines containing `import` → **Importers**; the rest → **Direct callers**
- Tests: `git grep -lw "${SYM}" -- '**/__tests__/**' '**/*.test.*'`

> Gotcha: `\b` and `\<\>` word boundaries do NOT work in `git grep -E` on macOS (BSD grep). Always use `-w` for whole-word matching.

**Report**, paste actual grep output, not a summary:

```
## Importers
<raw git grep output>

## Direct callers
<raw output, excluding the source file itself>

## Tests
<list of test files, or "none found, flag as risk">

## Risk surface
<N non-test files, M tests>. <one-sentence summary of what a change here would affect>
```

If the symbol is too common (e.g. `get`, `value`) and produces hundreds of matches, say so and ask the user to narrow.

Stop after the report. Do NOT propose edits, the report informs the user's next decision.
