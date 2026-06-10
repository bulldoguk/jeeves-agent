# Decisions

Architecture Decision Records for jeeves-agent, using the shared template
at `shared/templates/adr.md`. Each significant, hard-to-reverse design
call gets its own numbered file here — easier to find "why did we decide
X" later than digging through chat history or spec-section diffs.

Smaller calibration tweaks (thresholds, polling intervals, etc.) stay as
dated entries in [SPEC.md](../SPEC.md)'s "Decisions" log — only decisions
that shape the architecture or would be costly to reverse warrant a full
ADR.

| ADR | Title |
|---|---|
| [0001](0001-local-only-architecture.md) | Run Jeeves fully locally (no Claude API in the loop) |
| [0002](0002-sqlite-issue-tracking.md) | Track open issues in local SQLite |
| [0003](0003-learned-temperature-baselines.md) | Derive temperature baselines from HA history, not fixed config |
| [0004](0004-tier2-ollama-in-watchers.md) | Tier 2 judgment calls happen inside watchers, not in the poll loop |
| [0005](0005-ha-system-health-rest-only.md) | HA system health watcher uses REST only — no WebSocket in v1 |
