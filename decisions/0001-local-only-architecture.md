# ADR 0001: Run Jeeves fully locally (no Claude API in the loop)

## Status
Accepted

## Date
2026-06-07

## Context
Jeeves needs to make judgment calls beyond simple threshold checks (e.g.
"is this camera event burst a malfunction or a busy afternoon?"). Claude
would do this well, but it costs money per call, and Jeeves is meant to
poll continuously. Gary also said he may eventually move Jeeves onto
separate hardware away from the HA mini PC.

## Decision
Run Jeeves entirely locally for Phase 1 — no Claude API calls anywhere
in the loop. Use Ollama (already running locally) for any judgment calls
that go beyond simple rule/threshold checks. Architecture is kept
config-driven and not coupled to HA's add-on sandbox, so it can be lifted
onto separate hardware later without rework.

## Consequences
- Zero ongoing API cost, regardless of polling frequency.
- Works without an internet dependency.
- Judgment-call quality is bounded by what a mini-PC-class local model can
  do — this is acceptable for "flag it for Gary to look at," but would be
  a real constraint if Jeeves ever moves to acting autonomously.
- Leaves the door open to add a Claude-escalation tier later (see "hybrid"
  alternative below) if local judgment proves too weak for certain checks.

## Alternatives Considered
- **Pure Claude API for all judgment calls** — rejected on cost: the
  recurring per-poll cost scales directly with how often Jeeves checks in,
  which works against wanting frequent, low-latency monitoring.
- **Hybrid (local routine checks + Claude for hard judgment calls)** —
  not rejected, deferred. Revisit once Phase 1 shows what volume of
  genuinely "hard" cases the local tiers actually surface — if it's rare,
  occasional Claude calls become affordable; if it's frequent, the cost
  case weakens again.
