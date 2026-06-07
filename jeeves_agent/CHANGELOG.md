# Changelog

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
