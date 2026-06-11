# Changelog

## 0.3.8

- Raised `TEMPERATURE_STALE_MINUTES` from 30 to 90. Many Zigbee/ESPHome
  temperature sensors report on a ~60-minute cycle; the 30-minute threshold
  was generating false-stale alerts on every cycle for these devices.

## 0.3.4

- Fixed temperature anomaly false positives for Fahrenheit installs: the
  fixed-default fallback range was named `_C` but was raw numbers (-1 to 40),
  flagging normal °F readings (e.g. 74°F) as anomalous. New range is -50 to
  150 — unit-agnostic, catches only truly broken sensor values.
- Lowered `MIN_SAMPLES_FOR_LEARNED_BASELINE` from 50 to 20 so sensors that
  don't update constantly (e.g. stable-room sensors with low state-change rate)
  switch to the learned baseline sooner.

## 0.3.3

- Added HA Repairs monitoring to `check_ha_system_health`: polls
  `/api/repairs/issues` each cycle and raises an issue for any active
  (non-ignored, non-dismissed) repair. Resolves automatically when
  the repair is cleared.

## 0.3.2

- Fix first-run notification flood: on first start (or after HA restarts),
  Jeeves now skips existing error log content and only watches for new
  errors going forward. Previously it processed the entire log history on
  first poll, generating a burst of notifications for pre-existing errors.

## 0.3.1

- Persistent notifications: issues now create a persistent notification in
  the HA UI (bell icon) on open and dismiss it on resolve — so open issues
  are always visible in HA, not just as transient mobile push alerts.
- Resolved notification message now includes the original issue summary
  rather than just the raw issue key.

## 0.3.0

- Added `check_camera_event_rate`: counts daily motion events on
  `binary_sensor.*_motion` entities and flags when today's count exceeds
  5× the rolling daily average. Requires 3 days of history before flagging;
  skips cameras whose historical average is zero.
- Added `check_ha_system_health`: three REST-based checks each poll cycle —
  unavailable/unknown entities (5-minute grace period), pending software
  updates (`update.*` entities with state `"on"`), and new ERROR/CRITICAL
  lines in the HA error log. Error log tracking uses a byte offset persisted
  in SQLite, resetting automatically on HA restart.
- Added Ollama client (`jeeves/ollama_client.py`) for future Tier 2 judgment
  calls. Activated by setting `OLLAMA_URL`; runs as Tier 1-only when absent.
- New config options: `watch_camera_motion_entities`, `ollama_url`
  (renamed from `ollama_host`), `ollama_model` (default `llama3.2`).
- Fixed `get_history` — the `hours` parameter was accepted but never passed
  to the HA API, so all history calls were silently returning ~24h.
- Stale check thresholds split: temperature sensors 30 min, cameras 10 min.

## 0.2.0

- Added temperature anomaly watcher (`jeeves/baselines.py` +
  `check_temperature_anomalies`): derives a per-sensor "normal" range
  directly from HA's existing history (`/api/history/period`) — no
  warm-up period needed for sensors with normal history. Sensors with
  too little history (< 50 samples) fall back to a loose fixed sanity
  range (-1°C to 40°C) until enough history accumulates.
- Anomaly threshold: reading more than 3 standard deviations from its
  own historical mean.

## 0.1.0

- Initial skeleton: connects to Home Assistant, polls watched entities for
  staleness (no updates within threshold), tracks open issues in SQLite,
  and raises/clears notifications via the configured `notify` service.
- This is a walking skeleton — temperature-baseline learning, camera
  event-rate comparison, system-health, and update checks are not yet
  implemented (see SPEC.md in the project knowledge base).
