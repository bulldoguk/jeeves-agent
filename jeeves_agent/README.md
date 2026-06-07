# Jeeves Agent — Home Assistant Add-on

A local monitoring agent for Home Assistant. Watches for anomalous
behavior (temperatures, camera activity, system health, available
updates) and raises HA notifications when something looks off.

Runs entirely locally — no cloud / external LLM API calls.

## Status

Early skeleton (v0.1.0): connects to HA, polls watched entities for
staleness, and notifies on new/resolved issues. Most of the planned
detection logic (learned temperature baselines, camera event-rate
comparison, system-health and update checks) is not yet built.

## Installation

1. In Home Assistant, go to **Settings → Add-ons → Add-on Store**
2. Click the three-dot menu (⋮) → **Repositories**
3. Add: `https://github.com/bulldoguk/jeeves-agent`
4. Find **Jeeves Agent** in the store and click **Install**

## Configuration

| Option | Description |
|---|---|
| `ha_url` | Base URL of the HA API (default `http://supervisor/core` works inside the add-on sandbox) |
| `ha_token` | Long-lived access token — read entities/history, call `notify` |
| `notify_target` | HA notify service to send alerts to, e.g. `notify.mobile_app_garys_phone` |
| `poll_interval_minutes` | How often to run checks (default 5) |
| `ollama_host` / `ollama_model` | Local Ollama instance for judgment-call checks (not yet used) |
| `watch_temperature_entities` | List of temperature sensor entity IDs to watch |
| `watch_camera_entities` | List of camera/event entity IDs to watch |

## Data persistence

Issue tracking state is stored in `/share/jeeves_agent/jeeves.db` (SQLite)
— persists across add-on restarts and updates.

## How it works (current skeleton)

Each poll cycle, registered watchers (see `jeeves/watchers.py`) check the
watched entities and return a list of currently-open issues. The agent
diffs that against previously-open issues in SQLite:

- New issue → notification sent, recorded as open
- Still open → recorded, no repeat notification
- No longer reported → "resolved" notification sent, removed from store

Adding a new check is a matter of writing a new watcher function and
registering it in `WATCHERS` — the poll loop and notification/dedup logic
is shared.
