# Jeeves Agent — Domain Glossary

Terms used in this project. Implementation details and decisions belong in SPEC.md and decisions/ — not here.

---

**Issue** — A currently-active anomaly that Jeeves has detected and is tracking. An issue has a unique key, a human-readable summary, and an open/closed state persisted in SQLite. Jeeves notifies Gary when an issue opens and again when it clears. Not to be confused with HA Repairs issues (see below).

**Watcher** — A function that inspects some aspect of the HA environment and returns zero or more Issues. The poll loop runs all registered watchers each cycle and diffs their output against currently open Issues to decide what to notify.

**Tier 1 check** — A watcher that uses deterministic rules or thresholds (value out of range, entity offline, update available). Cheap; runs on every poll.

**Tier 2 check** — A watcher that invokes Ollama to make a judgment call that can't be resolved by a simple rule (e.g. "is this camera event burst a malfunction or a busy afternoon?"). Only called when Tier 1 flags something ambiguous.

**Baseline** — The "normal" range derived from a sensor's own historical readings. For temperature sensors: mean ± 3 standard deviations from HA history. For camera event rate: rolling daily average of motion events.

**Stale entity** — An entity that hasn't reported a state update within `STALE_THRESHOLD_MINUTES` (currently 30 minutes). Distinct from an entity in `unavailable` state — a stale entity is still reporting a value, just not recently.

**Zombie entity** — An entity in `unavailable` or `unknown` state for longer than a grace period. Term borrowed from HAGHS. Jeeves uses this for HA system health monitoring, restricted to physical device domains.

**HA Repairs** — HA's built-in issue registry (the yellow banners in Settings → Repairs). Distinct from Jeeves Issues. Not accessible via REST API; not in Jeeves v1 scope.

**Motion event** — A state transition to `"on"` on a `binary_sensor.*_motion` entity, driven by the camera's ONVIF event subscription via the native Reolink HA integration. Used by Jeeves to measure camera event rate. Distinct from a RustyCam clip — both are triggered by the same ONVIF event but are independent pipelines.

**Watch entities** — The entities Jeeves is configured to monitor. Split by purpose: `watch_temperature_entities` (temperature sensors), `watch_camera_entities` (camera entities for stale/offline check), `watch_camera_motion_entities` (motion binary sensors for event-rate check).
