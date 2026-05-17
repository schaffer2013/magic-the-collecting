# Agent Instructions

## API documentation stays current

Whenever a change adds, removes, renames, or materially changes an HTTP endpoint,
request/response field, status code, authentication behavior, or CSV export
shape, update `API.md` in the same change.

Treat `API.md` as a living contract for callers, not an after-the-fact summary.
If implementation and documentation disagree, fix the documentation or the code
before considering the work complete.

## Product reminders

- A collection may contain multiple owned copies of the same exact Scryfall
  printing. Do not model collection cards as unique by printing ID.
- The service should support multiple collections even if the first deployment
  only uses one.
- A submitted card should enter its target collection immediately as an
  unverified collection-card record, then transition to verified later.
