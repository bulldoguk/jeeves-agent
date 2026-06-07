"""
Watcher registry. Each watcher is a function:

    watcher(ha_client, config) -> list[Issue]

where Issue is (key, summary). Returning an issue means "this is currently
a problem"; the poll loop diffs against open issues to decide what to
notify about and what to clear.

Adding a new check = write a function and register it below — no changes
to the poll loop required.
"""

from collections import namedtuple

Issue = namedtuple("Issue", ["key", "summary"])

STALE_THRESHOLD_MINUTES = 30


def check_stale_entities(ha_client, config, now):
    """Flag any watched entity that hasn't updated in STALE_THRESHOLD_MINUTES.

    This is the simplest possible anomaly: "this thing has gone quiet."
    It applies equally well to a temperature sensor and a camera — both
    should be reporting regularly, and silence usually means something
    is wrong (offline, integration error, dead battery).
    """
    issues = []
    entities = config.watch_temperature_entities + config.watch_camera_entities
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
        if age_minutes is not None and age_minutes > STALE_THRESHOLD_MINUTES:
            issues.append(
                Issue(
                    key=f"stale:{entity_id}",
                    summary=(
                        f"{entity_id} hasn't reported in "
                        f"{int(age_minutes)} minutes (expected every "
                        f"{STALE_THRESHOLD_MINUTES})"
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
]
