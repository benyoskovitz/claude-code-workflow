---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/migrations/**"
---

<!--
  EXAMPLE path-scoped rule. Note the frontmatter is on line 1, nothing before it.
  This rule only enters context when the agent reads a .ts/.tsx file or anything
  under a migrations/ directory. Replace the globs and the body with your stack.

  Good candidates for a rule like this: framework gotchas, ORM/query footguns,
  timeout ceilings, serialization rules that bite at runtime, the tactical
  knowledge that's true for your stack but irrelevant on a non-coding session.
-->

# <Stack> tactical patterns

## <Pattern name, e.g. "Values crossing an async boundary must be serializable">

<State the rule as a hard constraint, then the failure mode it prevents, then the
fix. The most useful version of a rule like this names the specific incident that
taught it to you, a rule with a scar attached gets followed.>

Example shape:

> Anything returned across <boundary> must be <constraint>. A `Map` serializes to
> `{}` and every downstream `.get()` throws `is not a function`. Use a plain object
> instead. (Learned the hard way when <one-line incident>.)

## <Second pattern>

<...>
