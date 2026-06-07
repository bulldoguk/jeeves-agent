# ADR 0003: Derive temperature baselines from HA history, not fixed config

## Status
Accepted

## Date
2026-06-07

## Context
To flag an "anomalous" temperature reading, Jeeves needs to know what's
normal for that specific sensor. Hand-maintained per-sensor min/max
config is high-upkeep — different rooms run at different temperatures,
and "normal" shifts with the seasons. Initially we assumed Jeeves would
need a warm-up period to accumulate enough fresh history before it could
learn a baseline — but HA's recorder already retains history for most
entities (typically ~10 days of raw state history, plus indefinite
long-term statistics for numeric sensors).

## Decision
On each check, derive the sensor's "normal" range directly from its
existing HA history, queried via `/api/history/period`
(`ha_client.get_history`) — no warm-up period required for sensors with
normal history. Compute mean and standard deviation from the historical
readings; flag the current value as anomalous if it's more than 3
standard deviations from that mean (`jeeves/baselines.py`). Only fall
back to a loose fixed sanity range (-1°C to 40°C) for genuinely sparse
entities — fewer than 50 historical samples (e.g. a sensor added
yesterday).

## Consequences
- No hand-maintained per-sensor config to keep in sync with seasons,
  room changes, or new sensors being added.
- Each sensor's baseline naturally reflects its own character — a
  freezer and a living room each get a sensible "normal" range without
  Gary having to specify either.
- Depends on HA's recorder actually retaining useful history for the
  entity in question; brand-new sensors run on the loose fixed default
  until they accumulate enough samples to "graduate" to a learned
  baseline.
- The "is this anomalous" judgment is purely statistical (3 std devs) —
  it won't catch slow, gradual drift that stays within historical bounds.
  That's an acceptable v1 limitation; flagged as a possible future
  refinement if it proves to matter in practice.

## Alternatives Considered
- **Fixed config per sensor** — rejected: requires upkeep as seasons,
  rooms, and the sensor inventory change; doesn't scale as more sensors
  get added.
- **Accumulate fresh history before learning (a real warm-up period)** —
  rejected once we recognized HA's recorder already retains history;
  querying what already exists is strictly better than waiting to collect
  it again from scratch.
