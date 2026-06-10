# Jeeves Agent — Spec (v0.1, draft)

> Repo: https://github.com/bulldoguk/jeeves-agent — v0.2.0 pushed: connects
> to HA, polls watched entities for staleness, flags temperature readings
> outside their own history-derived baseline, tracks open issues in SQLite,
> raises/clears notifications. Install via **Settings → Add-ons → Add-on
> Store → ⋮ → Repositories** and add the repo URL above.

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

- **Temperature baselines: learned from history — pulled immediately,
  not accumulated over time.** HA's recorder already retains history
  (typically ~10 days of raw state history, plus long-term statistics
  indefinitely for numeric sensors like temperature). Jeeves queries
  `/api/history/period` (already wired in `ha_client.get_history`) on
  first run and derives the baseline from whatever HA already has — no
  warm-up period required for sensors with normal history.
  - **Cold start fallback:** only kicks in for genuinely sparse entities
    (e.g. a sensor added a day ago with too little history to trust). In
    that case, fall back to loose fixed sanity-check ranges (e.g. "nothing
    indoors should be below freezing or above 40°C") until enough history
    accumulates.
- **Camera anomalies (v1):** two checks —
  1. Camera goes offline / stops reporting — heartbeat check on the
     camera entity itself (`watch_camera_entities` in config).
  2. Event rate is way outside that camera's own historical norm — uses
     HA history of `binary_sensor.*_motion` entities (`watch_camera_motion_entities`
     in config, configured separately from the camera entities). Counts
     daily state transitions to `"on"`; flags when today's count exceeds
     **5× the rolling daily average**. Motion sensor history is used
     directly — no dependency on RustyCam's SQLite log.
  Tamper/obstruction-pattern detection (frozen frame, sudden permanent
  darkness, etc.) is **not** in v1 — revisit once the above two are
  running and we see what real anomalies look like.
- **Polling interval: every 5–10 minutes.** Good balance of catching
  issues promptly without hammering the mini PC or Ollama.
- **Unavailable entity grace period: 5 minutes.** The system health watcher
  only raises an issue once an entity has been continuously `unavailable` or
  `unknown` for at least 5 minutes. Uses `first_seen` already stored in
  IssueStore. Absorbs the brief unavailability flicker that occurs during HA
  restarts and add-on updates without adding new state.
- **Stale thresholds split by entity type:** `TEMPERATURE_STALE_MINUTES = 30`,
  `CAMERA_STALE_MINUTES = 10`. Motion binary sensors (`watch_camera_motion_entities`)
  are excluded from the stale check — silence on a motion sensor is normal
  (no motion); the camera entity stale check already covers "is this camera alive."
- **Issue tracking: local SQLite**, mirroring RustyCam's event-log
  pattern — persisted under `/share/jeeves_agent/`, easy to inspect,
  consistent with the existing add-ons.
- **HA access: scoped long-lived access token** — read-only on entities
  and history, plus permission to call the `notify` service. No config or
  device-control access (mirrors RustyCam/Forex Trader's least-privilege
  setup, and keeps risk low even if the token leaks or the agent
  misbehaves).

## Decisions (from interview, 2026-06-10)

- **Tier 2 (Ollama) is Phase 1**, not deferred. Watchers that need
  judgment call `ollama_client` directly — the poll loop stays unchanged.
  See ADR 0004.
- **Ollama client: raw `requests`**, no `ollama` library. Lives in
  `jeeves/ollama_client.py`. URL is configurable via `OLLAMA_URL` env var.
  **Ollama is optional:** if `OLLAMA_URL` is not set, `ollama_client` is
  `None`, watchers skip their Tier 2 judgment calls silently, and no
  "Tier 2 unavailable" issue is raised. Jeeves runs as Tier 1-only until
  Ollama is reachable. When the brain server is ready, setting `OLLAMA_URL`
  activates Tier 2 with no code changes. "Tier 2 unavailable" is only
  raised when Ollama is configured but unreachable (i.e. something broken,
  not intentionally absent).
- **Ollama unavailable → raise a `jeeves_tier2_unavailable` issue** rather
  than silently skipping judgment calls or flooding Gary with false
  positives. One notification that Tier 2 is offline; clears when it
  comes back.
- **Camera config split:** `watch_camera_entities` (camera entities, for
  stale/offline check) and `watch_camera_motion_entities` (motion binary
  sensors, for event-rate check) are separate config keys. Entity naming
  is not reliably derivable by convention (e.g. `front_door_ptz` maps to
  "Garage ptz" in HA).
- **HA system health watcher — v1 scope (REST only, three checks):**
  1. Unavailable entities — `GET /api/states` filtered to physical device
     domains (sensor, binary_sensor, camera, etc.) in `unavailable` or
     `unknown` state beyond a grace period.
  2. Software updates — `GET /api/states` filtered to `update` domain,
     state `"on"` = update available.
  3. Error log — `GET /api/error_log` for `ERROR`/`CRITICAL` lines.
  Integration config-entry states and Repairs require WebSocket and are
  not in v1. Integration failures surface as unavailable entities anyway.
  HAGHS (home-assistant-global-health-score) was evaluated as a data
  source but rejected — it exposes a single sensor blob rather than clean
  per-issue signals, and coupling Jeeves to another add-on's availability
  is the wrong shape for a monitoring agent.
- **Error log tracking:** store the character offset of the last processed
  position in SQLite. On each poll, also fetch `GET /api/` to check HA's
  `start_time` — if HA restarted since last poll, reset offset to 0 so
  post-restart errors are never missed.

## Remaining open questions

- [x] Minimum history threshold for a *new/sparse* sensor to switch from
      the fixed-default fallback to a learned baseline — **50 samples**
      (already implemented in `jeeves/baselines.py`). Most sensors won't
      hit this path since HA already retains history.
- [x] Camera event rate threshold — **5× rolling daily average** of
      motion sensor state transitions, using HA history of
      `binary_sensor.*_motion` entities (not RustyCam's SQLite log).
      Configured as a tuneable value; adjust if 5× proves too sensitive
      or too loose in practice.

## Explicitly deferred to later phases

- Auto-remediation of errors (restarting integrations, re-pairing devices).
- Auto-applying software/add-on updates.
- Escalation to Claude for harder judgment calls (cost-gated — revisit
  once Phase 1 shows what volume of "hard" cases actually shows up).
- Running off the HA mini PC on separate hardware.
