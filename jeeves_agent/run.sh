#!/usr/bin/with-contenv bashio

export HA_URL=$(bashio::config 'ha_url')
export HA_TOKEN=$(bashio::config 'ha_token')
export NOTIFY_TARGET=$(bashio::config 'notify_target')
export POLL_INTERVAL_MINUTES=$(bashio::config 'poll_interval_minutes')
export OLLAMA_URL=$(bashio::config 'ollama_url')
export OLLAMA_MODEL=$(bashio::config 'ollama_model')
export WATCH_TEMPERATURE_ENTITIES=$(bashio::config 'watch_temperature_entities | join(",")')
export WATCH_CAMERA_ENTITIES=$(bashio::config 'watch_camera_entities | join(",")')
export WATCH_CAMERA_MOTION_ENTITIES=$(bashio::config 'watch_camera_motion_entities | join(",")')
export WATCH_HUMIDITY_ENTITIES=$(bashio::config 'watch_humidity_entities | join(",")')
export CIRCUIT_SWITCHES=$(bashio::config 'circuit_switches | join(",")')

export DATA_DIR=/share/jeeves_agent
mkdir -p "${DATA_DIR}"

bashio::log.info "Starting Jeeves Agent — polling every ${POLL_INTERVAL_MINUTES}m"

# Force Python to flush stdout immediately so logs show up in the HA log viewer
export PYTHONUNBUFFERED=1

exec python3 /app/entrypoint.py
