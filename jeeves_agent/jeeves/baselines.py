"""
Derives "normal range" baselines for numeric sensors from HA history,
rather than relying on hand-maintained config (see SPEC.md).

HA's recorder already retains history for most entities, so a baseline
can usually be computed on the spot — no warm-up period needed. The
fixed-default fallback only matters for genuinely sparse entities (e.g.
a sensor that was added yesterday).
"""

from collections import namedtuple
from statistics import mean, stdev

Baseline = namedtuple("Baseline", ["low", "high", "source"])

MIN_SAMPLES_FOR_LEARNED_BASELINE = 50
STD_DEVS_FOR_ANOMALY = 3

# Loose sanity range used when there isn't enough history yet to learn
# a baseline. Wide on purpose — this is a safety net, not a real check.
FIXED_DEFAULT_LOW_C = -1.0
FIXED_DEFAULT_HIGH_C = 40.0


def numeric_values(history):
    """Extract numeric sensor values from a list of HA history states,
    skipping unavailable/unknown/non-numeric entries."""
    values = []
    for state in history:
        try:
            values.append(float(state["state"]))
        except (KeyError, TypeError, ValueError):
            continue
    return values


def derive_baseline(history):
    """Compute a Baseline from history, falling back to a fixed sanity
    range when there isn't enough data to trust a learned one."""
    values = numeric_values(history)

    if len(values) >= MIN_SAMPLES_FOR_LEARNED_BASELINE:
        center = mean(values)
        spread = stdev(values)
        return Baseline(
            low=center - STD_DEVS_FOR_ANOMALY * spread,
            high=center + STD_DEVS_FOR_ANOMALY * spread,
            source="learned",
        )

    return Baseline(
        low=FIXED_DEFAULT_LOW_C,
        high=FIXED_DEFAULT_HIGH_C,
        source="fixed-default",
    )


def is_anomalous(value, baseline):
    return value < baseline.low or value > baseline.high
