"""
Watcher registry. Each watcher is a function:

    watcher(ha_client, ollama_client, store, config, now) -> list[Issue]

where Issue is (key, summary). Returning an issue means "this is currently
a problem"; the poll loop diffs against open issues to decide what to
notify about and what to clear.

Adding a new check = write a function and register it below — no changes
to the poll loop required.
"""

import re
from collections import namedtuple, defaultdict
from datetime import datetime

from jeeves.baselines import derive_baseline, is_anomalous, numeric_values

Issue = namedtuple("Issue", ["key", "summary"])

TEMPERATURE_STALE_MINUTES = 30
CAMERA_STALE_MINUTES = 10
HISTORY_WINDOW_HOURS = 24 * 10  # matches HA's typical default recorder retention
CAMERA_EVENT_RATE_MULTIPLIER = 5
MIN_CAMERA_HISTORY_DAYS = 3  # need at least this many past days to trust the average
UNAVAILABLE_GRACE_MINUTES = 15

# Physical device domains where unavailable/unknown signals a real problem.
# Excludes: helpers (input_*), automations, scripts, persons, zones, buttons/events
# (default state is unknown until first interaction), and config-value domains
# (number, text, select) which custom integrations use for settings storage —
# those going unknown doesn't mean a physical device is offline.
ZOMBIE_DOMAINS = frozenset([
    "alarm_control_panel", "binary_sensor", "camera", "climate", "cover",
    "device_tracker", "fan", "humidifier", "lawn_mower", "light", "lock",
    "media_player", "remote", "sensor", "siren",
    "switch", "vacuum", "valve", "water_heater",
])

# When this many or more entities from the same apparent source go unavailable
# at once, collapse them into a single group notification instead of one per entity.
UNAVAILABLE_GROUP_THRESHOLD = 3

_LOG_LEVEL_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} (ERROR|CRITICAL)")
_LOG_LOGGER_RE = re.compile(r"\[([^\]]+)\]")


def check_stale_entities(ha_client, ollama_client, store, config, now):
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


def check_temperature_anomalies(ha_client, ollama_client, store, config, now):
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


def check_camera_event_rate(ha_client, ollama_client, store, config, now):
    """Flag motion sensors whose event rate today is way outside their own
    historical norm (5× the rolling daily average).

    Uses HA history of binary_sensor.*_motion entities. Requires at least
    MIN_CAMERA_HISTORY_DAYS of past data before flagging — new cameras run
    silently until their baseline is established.

    Skips cameras whose historical average is zero (never or rarely fires)
    to avoid false positives on quiet outdoor cameras at night.
    """
    issues = []
    today_key = now.date().isoformat()

    for entity_id in config.watch_camera_motion_entities:
        try:
            history = ha_client.get_history(entity_id, hours=HISTORY_WINDOW_HOURS)
        except Exception as exc:
            issues.append(
                Issue(
                    key=f"unreachable:{entity_id}",
                    summary=f"Could not read {entity_id} from Home Assistant ({exc})",
                )
            )
            continue

        daily_counts = _count_daily_on_transitions(history)
        past_counts = {day: count for day, count in daily_counts.items() if day != today_key}

        if len(past_counts) < MIN_CAMERA_HISTORY_DAYS:
            continue

        avg = sum(past_counts.values()) / len(past_counts)
        if avg == 0:
            continue

        today_count = daily_counts.get(today_key, 0)
        if today_count > avg * CAMERA_EVENT_RATE_MULTIPLIER:
            issues.append(
                Issue(
                    key=f"camera_event_rate:{entity_id}",
                    summary=(
                        f"{entity_id} has fired {today_count} motion events today "
                        f"({avg:.1f} daily average, {CAMERA_EVENT_RATE_MULTIPLIER}× "
                        f"threshold = {avg * CAMERA_EVENT_RATE_MULTIPLIER:.0f})"
                    ),
                )
            )
    return issues


def _count_daily_on_transitions(history):
    """Count 'on' state transitions per UTC date from HA history."""
    counts = defaultdict(int)
    for state in history:
        if state.get("state") != "on":
            continue
        ts = state.get("last_changed", "")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            counts[dt.date().isoformat()] += 1
        except ValueError:
            continue
    return dict(counts)


def _minutes_since(iso_timestamp, now):
    try:
        then = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (now - then).total_seconds() / 60


def check_ha_system_health(ha_client, ollama_client, store, config, now):
    """Three REST-based HA health checks: unavailable entities, pending
    software updates, and ERROR/CRITICAL lines in the error log.

    All three share a single GET /api/states call for efficiency. Error log
    tracking uses a byte offset persisted in metadata so Jeeves only
    processes new content each cycle, resetting on HA restart.
    """
    issues = []

    try:
        all_states = ha_client.get_all_states()
    except Exception as exc:
        issues.append(Issue(
            key="ha_api_unreachable",
            summary=f"Could not reach Home Assistant API ({exc})",
        ))
        return issues

    # Build set of entities suppressed because their circuit switch is off.
    # Config entries are "switch_entity_id:light_entity_id" pairs; when the
    # switch is off the downstream light being unavailable is expected.
    state_map = {s["entity_id"]: s.get("state") for s in all_states}
    circuit_suppressed = set()
    for mapping in getattr(config, "circuit_switches", []):
        if ":" not in mapping:
            continue
        switch_id, entity_id = mapping.split(":", 1)
        if state_map.get(switch_id.strip()) in ("off", "unavailable"):
            circuit_suppressed.add(entity_id.strip())

    # Unavailable entities — grouped by source prefix to avoid per-entity floods.
    # When many entities share the same name prefix (e.g. "road_glide_", "traverse_"),
    # they likely belong to the same integration/device; collapsing them into one
    # issue prevents a single bridge outage from generating hundreds of notifications.
    unavail_by_prefix: dict[str, list[str]] = defaultdict(list)

    for state in all_states:
        entity_id = state.get("entity_id", "")
        domain = entity_id.split(".")[0] if "." in entity_id else ""
        if domain not in ZOMBIE_DOMAINS:
            continue
        if state.get("state") not in ("unavailable", "unknown"):
            continue
        if entity_id in circuit_suppressed:
            continue
        last_changed = state.get("last_changed")
        age_minutes = _minutes_since(last_changed, now) if last_changed else None
        if age_minutes is None or age_minutes < UNAVAILABLE_GRACE_MINUTES:
            continue
        # Derive a grouping prefix: first two underscore-separated words of the
        # object_id (e.g. "road_glide_oil_change_interval_days" → "road_glide").
        object_id = entity_id.split(".", 1)[-1] if "." in entity_id else entity_id
        parts = object_id.split("_")
        prefix = "_".join(parts[:2]) if len(parts) >= 3 else object_id
        unavail_by_prefix[prefix].append((entity_id, state.get("state", "unavailable"), int(age_minutes)))

    for prefix, entries in unavail_by_prefix.items():
        if len(entries) >= UNAVAILABLE_GROUP_THRESHOLD:
            oldest = max(age for _, _, age in entries)
            sample = entries[0][0]
            issues.append(Issue(
                key=f"unavailable_group:{prefix}",
                summary=(
                    f"{len(entries)} entities unavailable (prefix '{prefix}', "
                    f"e.g. {sample}; oldest {oldest} min)"
                ),
            ))
        else:
            for entity_id, state_str, age_minutes in entries:
                issues.append(Issue(
                    key=f"unavailable:{entity_id}",
                    summary=f"{entity_id} has been {state_str} for {age_minutes} minutes",
                ))

    # Pending software updates
    for state in all_states:
        entity_id = state.get("entity_id", "")
        if not entity_id.startswith("update."):
            continue
        if state.get("state") != "on":
            continue
        attrs = state.get("attributes", {})
        title = attrs.get("title") or attrs.get("friendly_name") or entity_id
        installed = attrs.get("installed_version", "?")
        latest = attrs.get("latest_version", "?")
        issues.append(Issue(
            key=f"update_available:{entity_id}",
            summary=f"{title} update available: {installed} → {latest}",
        ))

    # HA Repairs
    try:
        repairs = ha_client.get_repairs()
    except Exception as exc:
        issues.append(Issue(
            key="repairs_unreachable",
            summary=f"Could not read HA repairs ({exc})",
        ))
        repairs = []

    for repair in repairs:
        if repair.get("ignored") or repair.get("dismissed_version"):
            continue
        issue_id = repair.get("issue_id", "unknown")
        domain = repair.get("domain", "")
        severity = repair.get("severity", "warning")
        translation_key = repair.get("translation_key") or issue_id
        issues.append(Issue(
            key=f"repair:{domain}:{issue_id}",
            summary=f"HA repair [{severity}] {domain}: {translation_key}",
        ))

    # Error log — new ERROR/CRITICAL lines since last poll
    try:
        ha_start_time = ha_client.get_start_time()
        log_text = ha_client.get_error_log()
    except Exception as exc:
        issues.append(Issue(
            key="error_log_unreachable",
            summary=f"Could not read HA error log ({exc})",
        ))
        return issues

    first_run = store.get_meta("ha_start_time") == ""
    if first_run or ha_start_time != store.get_meta("ha_start_time"):
        store.set_meta("ha_start_time", ha_start_time)
        # On first run or HA restart, skip existing log content — only watch
        # for new errors from this point forward.
        store.set_meta("error_log_offset", len(log_text))
        return issues

    offset = int(store.get_meta("error_log_offset", "0"))
    new_content = log_text[offset:]
    store.set_meta("error_log_offset", len(log_text))

    # Key errors by logger + date so each logger raises at most one issue
    # per day — avoids a burst of identical notifications for a noisy component.
    today = now.date().isoformat()
    seen = {}
    for line in new_content.splitlines():
        m_level = _LOG_LEVEL_RE.match(line)
        if not m_level:
            continue
        m_logger = _LOG_LOGGER_RE.search(line)
        logger = m_logger.group(1) if m_logger else "unknown"
        seen[logger] = (m_level.group(1), line.strip())

    for logger, (level, line) in seen.items():
        issues.append(Issue(
            key=f"log_error:{logger}:{today}",
            summary=f"HA log {level} [{logger}]: {line[:200]}",
        ))

    return issues


# Registered watchers, run in order each poll cycle.
WATCHERS = [
    check_stale_entities,
    check_temperature_anomalies,
    check_camera_event_rate,
    check_ha_system_health,
]
