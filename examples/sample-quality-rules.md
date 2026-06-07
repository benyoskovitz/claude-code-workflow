# Quality Rules

<!--
  Hand-authored rules that /code-watch's quality pass grades changes against.
  Each H2 is a category (the skill groups findings by these). Each bullet is a
  concrete, checkable rule that can be verified against a diff. Keep them specific:
  "every mutation revalidates affected caches" is checkable; "write good code" is not.

  This is a generic starter set. Replace it with the standards that actually matter
  in your project. The most useful rules are the ones that encode a mistake you've
  already made once.
-->

## Data integrity

- Every mutation revalidates or invalidates the caches and views it affects.
- Storage column types match what the code writes (no string written into a numeric column).
- Money and quantities are validated as finite numbers before they are stored.
- Conflict keys on an upsert match an actual unique constraint.

## Error handling

- No empty catch blocks. At minimum, log the real error.
- User-facing error messages say what happened and what to do next, not "something went wrong."
- Async work in request handlers is awaited. No fire-and-forget on serverless.
- Loops and polls have a maximum duration so they cannot hang forever.

## UX consistency

- Every data fetch has a loading state and an empty state.
- Destructive actions confirm before they run.
- Buttons disable while a submit is in flight, to prevent double-clicks.
- Formatting is consistent (currency with separators, dates in one format).

## Architecture

- Types come from the shared types module, not redefined inline.
- No new utility file when an existing shared one already covers the need.
- New modules follow the established folder structure for their layer.
- Server-side logic stays server-side; nothing sensitive leaks to the client.

## Testing

- New business logic ships with a test, or a one-line note explaining why it doesn't.
- Tests assert on behavior, not implementation details.
- Edge cases are covered: empty input, unauthorized access, and the error path.
