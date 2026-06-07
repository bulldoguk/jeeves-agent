# Jeeves Agent — Spec (v0.1, draft)

> Repo: https://github.com/bulldoguk/jeeves-agent — initial walking-skeleton
> scaffold pushed (v0.1.0): connects to HA, polls watched entities for
> staleness, tracks open issues in SQLite, raises/clears notifications.
> Install via **Settings → Add-ons → Add-on Store → ⋮ → Repositories** and
> add the repo URL above.

## Goal

A monitoring agent for Home Assistant that watches for anomalous behavior
and surfaces it via HA notifications. Starts as a **watcher + alerter**;
auto-remediation is a later phase, gated on the watcher proving reliable.

## Phase 1 scope (this spec)

- Run **fully local** — no Claude API calls, no cloud dependency.
- Lives on the HA mini PC initially; built so it can be lifted onto a
  separate machine later without rework (config-driven HA connection,
  no hard dependency on running *inside* HA's add-on sandbox).
- Uses **Ollama** (already running locally) for any judgment calls that
  go beyond simple threshold/rule checks.
- **Does not take remediation actions yet** — it raises notifications only.
  Auto-remediation (restarting integrations, applying updates, etc.) is
  Phase 2, and only after Phase 1 has run reliably for a while.

## What it watches (v1)

1. **Temperature sensors** — flag readings outside expected range for the
   entity/room/time-of-day, or sensors that stop reporting (stale data).
2. **Camera activity** — flag cameras that go offline, stop producing
   events, or produce an abnormal burst of events (possible malfunction
   or tamper, vs. genuine activity).
3. **HA system health** — integration/entity error states, unavailable
   entities, repairs/issues raised by HA itself.
4. **Software updates** — new updates available for HA core, add-ons
   (incl. RustyCam, Forex Trader), HACS integrations, OS.

This list is expected to grow — design the watcher registry so adding a
new check is a small, isolated addition (not a rework of the core loop).

## How it talks to HA

- **Read side:** HA REST API / WebSocket API (entity states, history,
  `system_log`, `update.*` entities, repairs/issues).
- **Write side (notifications only, in v1):** HA `notify` service or
  persistent notifications, so alerts show up in the HA UI / mobile app
  Gary already uses — no new notification channel to maintain.

## Anomaly detection approach

- **Tier 1 — rules/thresholds:** cheap, deterministic checks (sensor
  offline > N minutes, value outside configured min/max, update available
  = true). Run these on every poll; they're the bulk of the workload.
- **Tier 2 — local LLM judgment (Ollama):** for cases that aren't a clean
  threshold call — e.g. "is this camera event burst a malfunction or just
  a busy afternoon?", "does this error log look benign or serious?".
  Only invoked when Tier 1 flags something ambiguous, to keep load on the
  mini PC reasonable.

## Notification design

- One notification per distinct issue (not per poll) — track issue state
  so Jeeves doesn't spam Gary every cycle for the same ongoing problem.
- Notification includes: what triggered it, the entity/area involved,
  current value vs. expected, and a timestamp.
- Resolved issues get a follow-up "back to normal" notification.

## Deployment

- Mirrors the pattern already used for RustyCam / Forex Trader: package
  as an HA add-on (or a standalone service if it ends up living off-box),
  config via the HA add-on config UI, logs/state persisted under
  `/share/jeeves_agent/`.

## Decisions (from interview, 2026-06-07)

- **Temperature baselines: learned from history.** Jeeves derives a
  per-sensor "normal" range from HA's historical data rather than relying
  on hand-maintained config.
  - **Cold start:** until enough history exists to trust a learned
    baseline, fall back to loose fixed sanity-check ranges (e.g. "nothing
    indoors should be below freezing or above 40°C") so Jeeves isn't
    silent — and isn't noisy — during warm-up.
- **Camera anomalies (v1):** two checks —
  1. Camera goes offline / stops reporting (heartbeat-style check).
  2. Event rate is way outside that camera's own historical norm (compare
     against its RustyCam event-log baseline, not a fixed number).
  Tamper/obstruction-pattern detection (frozen frame, sudden permanent
  darkness, etc.) is **not** in v1 — revisit once the above two are
  running and we see what real anomalies look like.
- **Polling interval: every 5–10 minutes.** Good balance of catching
  issues promptly without hammering the mini PC or Ollama.
- **Issue tracking: local SQLite**, mirroring RustyCam's event-log
  pattern — persisted under `/share/jeeves_agent/`, easy to inspect,
  consistent with the existing add-ons.
- **HA access: scoped long-lived access token** — read-only on entities
  and history, plus permission to call the `notify` service. No config or
  device-control access (mirrors RustyCam/Forex Trader's least-privilege
  setup, and keeps risk low even if the token leaks or the agent
  misbehaves).

## Remaining open questions

- [ ] How much history counts as "enough" to trust a learned temperature
      baseline — needs a concrete threshold (e.g. 2 weeks of data,
      minimum N readings) before switching off the fixed-default fallback.
- [ ] Exact "way outside historical norm" threshold for camera event
      rate — needs real RustyCam history to calibrate against (e.g. is
      3x the daily average too sensitive? 5x?).

## Explicitly deferred to later phases

- Auto-remediation of errors (restarting integrations, re-pairing devices).
- Auto-applying software/add-on updates.
- Escalation to Claude for harder judgment calls (cost-gated — revisit
  once Phase 1 shows what volume of "hard" cases actually shows up).
- Running off the HA mini PC on separate hardware.
