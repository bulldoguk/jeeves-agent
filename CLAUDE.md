# Jeeves Agent — Claude Instructions

type: coding

## Status
Planning

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

## Notes
- Sibling HA add-ons for reference/patterns: RustyCam (projects/rustycam),
  Forex Trader (projects/forex/ha-addon).
- May eventually move off the HA mini PC onto separate hardware — keep
  the design portable (config-driven HA connection, not sandbox-coupled).
