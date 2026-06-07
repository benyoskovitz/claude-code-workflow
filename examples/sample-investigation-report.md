# Investigation Report, add rate limiting to the public API

<!--
  This is what the agent produces BEFORE writing code, per the Maintenance Change
  Protocol in CLAUDE.md.template. Realistic, sanitized example. The last section
  (the rubric) gets written out to .rubric.md for /assess to read later.
-->

**Files read (with line ranges):**
- `src/api/middleware/index.ts` (1-80), middleware chain wiring
- `src/api/auth/keys.ts` (40-95), where the API key is resolved per request
- `src/config/index.ts` (1-60), config loading pattern
- `src/lib/store/client.ts` (1-50), shared store client (already used for sessions)

**Symbol(s) being changed:**
- `buildMiddlewareChain()`: `src/api/middleware/index.ts:22` (add limiter)
- new `rateLimiter()` middleware, new file `src/api/middleware/rate-limit.ts`

**Direct callers and importers (grep output):**
```
$ grep -rn "buildMiddlewareChain" src/
src/api/server.ts:14:  app.use(buildMiddlewareChain());
src/api/__tests__/middleware.test.ts:9:  const chain = buildMiddlewareChain();
```

**Tests covering this code path:**
- `src/api/__tests__/middleware.test.ts`: chain assembly. No rate-limit coverage yet, will add.

**Schema / contract impact:** None. No type or persistence change; limiter state lives in the existing shared store under a new key prefix.

**<Project footgun check>, in-process state across instances:** The limiter must not hold counters in module memory; this service runs multiple instances and per-process counters would let callers exceed the limit N-fold. Use the shared store. (This is the recurring failure mode this project keeps hitting, state that doesn't survive horizontal scaling.)

**Task rubric (written to `.rubric.md`):** see `sample-rubric.md` in this folder, 5 pillars: per-key enforcement, runtime config, internal bypass, restart-durable state, no regression.

**Open questions:**
- Window algorithm: fixed window is simpler; sliding window is fairer. Going fixed for v1 unless the limit needs to be tight. Flagged for the reviewer.

## Then propose

**Files to edit:**
- `src/api/middleware/rate-limit.ts` (new)
- `src/api/middleware/index.ts` (wire the limiter into the chain)
- `src/api/__tests__/rate-limit.test.ts` (new)

**Per-file change summary:**
- `rate-limit.ts`: middleware reading threshold/window from config, counting per key in the shared store, returning 429 + Retry-After over the limit, bypassing on the service token.
- `index.ts`: insert limiter after auth, before handlers.
- `rate-limit.test.ts`: the four behavioral assertions from the rubric.

**Verification plan:** `npm run build && npm run test:run`, then `/assess` against `.rubric.md`, then `/pre-commit`. If any pillar fails, re-enter Plan mode narrowed to that pillar, do not patch in place.
