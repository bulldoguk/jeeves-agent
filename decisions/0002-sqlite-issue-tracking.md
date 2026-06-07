# ADR 0002: Track open issues in local SQLite

## Status
Accepted

## Date
2026-06-07

## Context
Jeeves polls every 5–10 minutes, but shouldn't send a fresh notification
every cycle for the same ongoing problem — that would bury Gary in
duplicate alerts. It needs to remember which issues are currently "open"
so it can notify only on state changes (new issue → alert, issue clears →
"resolved" alert), and that memory needs to survive add-on restarts and
updates.

## Decision
Track open issues in a local SQLite database (`IssueStore` in
`jeeves/store.py`), persisted under `/share/jeeves_agent/jeeves.db` —
mirroring the pattern RustyCam already uses for its event log.

## Consequences
- Consistent with the existing add-ons (RustyCam) — same persistence
  location convention, same "simple file DB" mental model to maintain.
- Easy to inspect/debug directly (it's just a SQLite file under `/share/`).
- Survives add-on restarts and updates, so a routine update doesn't cause
  a burst of "new" notifications for issues that were already known.
- Adds a small file-based DB as a dependency, vs. piggybacking on
  something HA already provides.

## Alternatives Considered
- **HA helpers / `input_boolean` entities** — rejected: would clutter
  Gary's HA entity list with internal bookkeeping state, and couples
  Jeeves's plumbing to HA's UI in a way that doesn't add value (Gary
  doesn't need to see "is issue X open" as an HA entity).
- **In-memory only** — rejected: a restart (e.g. after an add-on update)
  would wipe Jeeves's memory of what it already alerted on, causing it to
  re-notify on everything still open — exactly the spam this is meant to
  avoid.
