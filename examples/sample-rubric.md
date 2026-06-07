# Task Rubric, add rate limiting to the public API
**Date:** 2026-06-07
**Branch:** feature/api-rate-limit

<!--
  A rubric is 3-5 MECE pillars (mutually exclusive, collectively exhaustive),
  each with a BINARY pass criterion and a stated verification method. Written
  BEFORE Execute, read by /assess AFTER. This is a realistic, sanitized example.
-->

1. **Limit enforced per API key**: requests above the configured threshold for a
   given key return HTTP 429 with a `Retry-After` header; requests under it pass
   through unchanged. Verify: integration test sends N+1 requests in the window,
   asserts the last is 429 and the first N are 200.

2. **Limits are configurable without a deploy**: the per-key threshold and window
   read from config at request time, not baked in at build. Verify: grep shows the
   handler reads the config value per call; changing the config value in a test
   changes the enforced limit with no rebuild.

3. **No limiting on internal/service traffic**: requests bearing the internal
   service token bypass the limiter entirely. Verify: test sends 10x the threshold
   with the service token, asserts all 200.

4. **Counter state survives a single instance restart**: the limiter uses the
   shared store, not in-process memory, so a restart doesn't reset a caller's
   window. Verify: grep confirms no module-level counter map; the store client is
   the source of truth.

5. **No regression in existing handlers**: build + full test suite green; the
   limiter middleware is additive and no existing route's behavior changed.
   Verify: `npm run build && npm run test:run` both pass.
