# HA system health watcher uses REST only — no WebSocket in v1

Jeeves needs to detect unhealthy HA states: unavailable entities, pending software updates, and error log entries. HA also exposes integration config-entry states (SETUP_ERROR, SETUP_RETRY, FAILED_UNLOAD) and the Repairs issue registry, but both require the WebSocket API — there are no REST endpoints for them. Adding WebSocket support means a new dependency, authentication handshake, message framing, and connection management, which is a significant complexity jump for an agent that is otherwise a simple REST poller. Integration config-entry failures also surface downstream as unavailable entities, which the REST-based zombie check already catches. WebSocket access to Repairs and config-entry states is deferred to a later phase if the REST-only set proves insufficient.

## Considered Options

- **HAGHS (home-assistant-global-health-score) as a data source** — rejected: HAGHS is a custom integration that runs inside HA and exposes a single sensor entity with all health data packed into `extra_state_attributes`. Jeeves would need to parse attribute blobs and depend on HAGHS being installed and healthy — the wrong shape for a monitoring agent. HAGHS is worth installing separately as a health dashboard, but not as a Jeeves dependency.
- **WebSocket client for config-entry states and Repairs** — not rejected, deferred. Revisit once Phase 1 is running and we can see whether missed integration failures (that don't surface as unavailable entities) are a real gap.
