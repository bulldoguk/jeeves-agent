"""
Watcher registry. Each watcher is a function:

    watcher(ha_client, ollama_client, config, now) -> list[Issue]

where Issue is (key, summary). Returning an issue means "this is currently
a problem"; the poll loop diffs against open issues to decide what to
notify about and what to clear.

Adding a new check = write a function and register it below — no changes
to the poll loop required.
"""

from collections import namedtuple

from jeeves.baselines import derive_baseline, is_anomalous, numeric_values

Issue = namedtuple("Issue", ["key", "summary"])

TEMPERATURE_STALE_MINUTES = 30
CAMERA_STALE_MINUTES = 10
HISTORY_WINDOW_HOURS = 24 * 10  # matches HA's typical default recorder retention


def check_stale_entities(ha_client, ollama_client, config, now):
    """Flag any watched entity that hasn't updated in STALE_THRESHOLD_MINUTES.

    This is the simplest possible anomaly: "this thing has gone quiet."
    It applies equally well to a temperature sensor and a camera — both
    should be reporting regularly, and silence usually means something
    is wrong (offline, integration error, dead battery).
    """
    issues = []
    checks = [
        (config.watch_temperature_entities, TEMPERATURE_STALE_MINUTES),
        (config.watch_camera_entities, CAMERA_STALE_MINUTES),
    ]
    for entities, threshold in checks:
        for entity_id in entities:
            try:
                state = ha_client.get_state(entity_id)
            except Exception as exc:
                issues.append(
                    Issue(
                        key=f"unreachable:{entity_id}",
                        summary=f"Could not read {entity_id} from Home Assistant ({exc})",
                    )
                )
                continue

            last_changed = state.get("last_changed")
            if last_changed is None:
                continue

            age_minutes = _minutes_since(last_changed, now)
            if age_minutes is not None and age_minutes > threshold:
                issues.append(
                    Issue(
                        key=f"stale:{entity_id}",
                        summary=(
                            f"{entity_id} hasn't reported in "
                            f"{int(age_minutes)} minutes (expected every "
                            f"{threshold})"
                        ),
                    )
                )
    return issues


def check_temperature_anomalies(ha_client, ollama_client, config, now):
    """Flag temperature readings that fall outside the sensor's own
    historical baseline (or, for sensors with too little history, outside
    a loose fixed sanity range — see jeeves.baselines).

    Each watched sensor gets its own baseline derived from its own
    history — a bedroom and a freezer have very different "normal"
    ranges, and this avoids hand-maintaining per-sensor config.
    """
    issues = []
    for entity_id in config.watch_temperature_entities:
        try:
            history = ha_client.get_history(entity_id, hours=HISTORY_WINDOW_HOURS)
            current_state = ha_client.get_state(entity_id)
        except Exception as exc:
            issues.append(
                Issue(
                    key=f"unreachable:{entity_id}",
                    summary=f"Could not read {entity_id} from Home Assistant ({exc})",
                )
            )
            continue

        values = numeric_values(current_state and [current_state] or [])
        if not values:
            continue
        current_value = values[0]

        baseline = derive_baseline(history)
        if is_anomalous(current_value, baseline):
            issues.append(
                Issue(
                    key=f"temp_anomaly:{entity_id}",
                    summary=(
                        f"{entity_id} reading {current_value:g} is outside its "
                        f"normal range ({baseline.low:.1f}–{baseline.high:.1f}, "
                        f"{baseline.source} baseline)"
                    ),
                )
            )
    return issues


def _minutes_since(iso_timestamp, now):
    from datetime import datetime

    try:
        then = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (now - then).total_seconds() / 60


# Registered watchers, run in order each poll cycle.
WATCHERS = [
    check_stale_entities,
    check_temperature_anomalies,
]
