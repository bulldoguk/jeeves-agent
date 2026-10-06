# Jeeves Agent

A local monitoring agent for Home Assistant. It watches the house for things going quietly wrong (sensors that stop reporting, rooms drifting outside their normal range, cameras that go silent, integrations that break) and sends a notification when an issue opens, then again when it clears.

Everything runs on your own hardware. No cloud services, no external APIs.

## What it checks

Each poll cycle (default every 5 minutes) runs a set of watchers against the HA REST API:

| Watcher | Raises an issue when |
|---|---|
| **Stale entities** | A watched temperature, humidity or camera entity hasn't reported for too long (90 minutes for slow-cycling Zigbee/ESPHome sensors) |
| **Temperature / humidity anomalies** | A reading sits more than 3 standard deviations from that sensor's *own* baseline, learned from HA history. Sensors with too little history fall back to a loose sanity range, so a °F install doesn't trip on 74°F |
| **Camera event rate** | A motion sensor's event count today is far outside its rolling daily average, in either direction |
| **HA system health** | Devices unavailable (grouped by device, so one bridge outage is one alert, not hundreds), pending updates, active HA Repairs, and new ERROR/CRITICAL lines in the error log |

Issues are de-duplicated in SQLite: you get one notification when something breaks and one when it recovers, not one per poll.

Lights on switched circuits are a common false alarm: turn the wall switch off and every bulb goes `unavailable`. The `circuit_switches` option suppresses those while the switch is off.

## Installation

1. In Home Assistant, go to **Settings → Add-ons → Add-on Store**
2. Open the ⋮ menu → **Repositories** and add `https://github.com/bulldoguk/jeeves-agent`
3. Find **Jeeves Agent** in the store and click **Install**

The add-on runs a prebuilt multi-arch image (`amd64`, `aarch64`) published to GHCR by GitHub Actions.

## Configuration

| Option | Description |
|---|---|
| `ha_url` | HA API base URL. The default `http://supervisor/core` works inside the add-on sandbox |
| `ha_token` | Long-lived access token: read states/history, call `notify` |
| `notify_target` | Notify service for alerts, e.g. `notify.mobile_app_your_phone` |
| `poll_interval_minutes` | How often to run the checks (1–60, default 5) |
| `watch_temperature_entities` | Temperature sensors to watch |
| `watch_humidity_entities` | Humidity sensors to watch |
| `watch_camera_entities` | Camera entities to check for staleness |
| `watch_camera_motion_entities` | Motion `binary_sensor`s used for the event-rate check |
| `circuit_switches` | `switch_entity:light_entity` pairs; the light's `unavailable` state is ignored while the switch is off |
| `ollama_url` / `ollama_model` | Local Ollama instance for future judgment-call checks (not used by the current watchers) |

State is stored in `/share/jeeves_agent/jeeves.db` and survives restarts and updates.

## Extending it

A watcher is a plain function, `(ha_client, ollama_client, store, config, now) -> list[Issue]`, registered in `WATCHERS` in `jeeves_agent/jeeves/watchers.py`. The poll loop, de-duplication and notifications are shared, so adding a new check is a matter of writing one function.

## Repository layout

| Path | Contents |
|---|---|
| `jeeves_agent/` | The add-on: manifest, Dockerfile, Python package, [changelog](jeeves_agent/CHANGELOG.md) |
| `decisions/` | Architecture decision records |
| `SPEC.md`, `CONTEXT.md` | Design spec and domain glossary |
