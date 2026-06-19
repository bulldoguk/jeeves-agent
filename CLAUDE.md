# Jeeves Agent — Claude Instructions

type: coding

## Status
Live — v0.3.9 running in HA

## Repo
- Local path: ~/Documents/Claude/projects/jeeves-agent
- Remote: https://github.com/bulldoguk/jeeves-agent
- Primary branch: main
- Add-on lives in `jeeves_agent/` (config.yaml, Dockerfile, run.sh,
  jeeves/ source package). `repository.yaml` at repo root makes it
  installable as a custom HA add-on repository.

## Overview
A local Home Assistant monitoring agent. Watches for anomalous behavior
(temperatures, camera activity, system errors, available updates) and
raises HA notifications when something looks off. Runs fully local
(Ollama on the HA mini PC) — no Claude API in the loop for now, to avoid
cost. Auto-remediation of issues/updates is a planned later phase, once
the watcher itself is proven reliable.

See [SPEC.md](SPEC.md) for the working spec, and [decisions/](decisions/)
for ADRs on significant architecture calls (local-only, SQLite issue
tracking, learned temperature baselines, etc.).

## Deployment
- HA add-on slug: `33b61970_jeeves_agent`
- Config uses a long-lived access token; `ha_url` must be `http://homeassistant.local:8123` — NOT `http://supervisor/core` (that proxy requires the supervisor token, which Jeeves doesn't use)
- SQLite DB persists across updates at `/share/jeeves_agent/jeeves.db`
- No ingress/ports — check logs via: `ssh root@homeassistant.local "ha addons logs 33b61970_jeeves_agent"`
- **As of v0.3.11**: prebuilt multi-arch image (`ghcr.io/bulldoguk/{arch}-addon-jeeves_agent`), built/pushed by `.github/workflows/build.yaml` on push to `main` (uses the official `home-assistant/builder` action). `jeeves_agent/build.yaml` is kept only as the builder's base-image input — Supervisor itself now pulls the prebuilt image instead of running `docker buildx` locally.
- After pushing a new version: wait for the GitHub Action to finish publishing the image (check the Actions tab) before doing anything on the HA side — `ha store reload` via SSH, then `ha_manage_addon update` + `start`. If `ha_manage_addon update` triggers a local build instead of a pull, the image tag/arch didn't match — check the Action's logs.

## Guardrails (as of v0.3.9)
- `ZOMBIE_DOMAINS` does NOT include `number`, `text`, or `select` — custom integrations (vehicle maintenance, shopping list, bug tracker) use those domains for config storage, not physical sensors
- `TEMPERATURE_STALE_MINUTES = 90` (raised from 30 in v0.3.8 — many Zigbee/ESPHome sensors report on ~60 min cycles)
- `UNAVAILABLE_GRACE_MINUTES = 15` (raised from 5 to absorb Zigbee flaps)
- Unavailable entities are grouped by two-word name prefix when 3+ share the same prefix — prevents a bridge outage from generating hundreds of individual notifications
- Mobile push notifications are **disabled** — Jeeves writes/dismisses HA persistent notifications only, until signal quality is confirmed
- `local_zigbee2mqtt2` add-on is intentionally in error/stopped state — do not investigate or try to fix it

## Notes
- Sibling HA add-ons for reference/patterns: RustyCam (projects/rustycam),
  Forex Trader (projects/forex/ha-addon).
- May eventually move off the HA mini PC onto separate hardware — keep
  the design portable (config-driven HA connection, not sandbox-coupled).
- Tier 2 / Ollama deferred until brain server hardware is available.
