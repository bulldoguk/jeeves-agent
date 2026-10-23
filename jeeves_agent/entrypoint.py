import os
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field

from jeeves.ha_client import HomeAssistantClient
from jeeves.matrix_client import MatrixClient
from jeeves.ollama_client import OllamaClient
from jeeves.store import IssueStore
from jeeves.watchers import WATCHERS


@dataclass
class Config:
    ha_url: str
    ha_token: str
    notify_target: str
    poll_interval_minutes: int
    watch_temperature_entities: list = field(default_factory=list)
    watch_humidity_entities: list = field(default_factory=list)
    watch_camera_entities: list = field(default_factory=list)
    watch_camera_motion_entities: list = field(default_factory=list)
    circuit_switches: list = field(default_factory=list)
    ollama_url: str = ""
    ollama_model: str = "llama3.2"
    matrix_homeserver: str = ""
    matrix_token: str = ""
    matrix_room: str = ""
    persistent_notifications: bool = True


def load_config():
    def split_entities(value):
        return [e.strip() for e in value.split(",") if e.strip()]

    def optional(value):
        # bashio::config prints "null" for an unset optional option.
        return "" if value == "null" else value

    return Config(
        ha_url=os.environ["HA_URL"],
        ha_token=os.environ["HA_TOKEN"],
        notify_target=os.environ.get("NOTIFY_TARGET", "notify.notify"),
        poll_interval_minutes=int(os.environ.get("POLL_INTERVAL_MINUTES", "5")),
        watch_temperature_entities=split_entities(
            os.environ.get("WATCH_TEMPERATURE_ENTITIES", "")
        ),
        watch_humidity_entities=split_entities(
            os.environ.get("WATCH_HUMIDITY_ENTITIES", "")
        ),
        watch_camera_entities=split_entities(
            os.environ.get("WATCH_CAMERA_ENTITIES", "")
        ),
        watch_camera_motion_entities=split_entities(
            os.environ.get("WATCH_CAMERA_MOTION_ENTITIES", "")
        ),
        circuit_switches=split_entities(
            os.environ.get("CIRCUIT_SWITCHES", "")
        ),
        ollama_url=os.environ.get("OLLAMA_URL", ""),
        ollama_model=os.environ.get("OLLAMA_MODEL", "llama3.2"),
        matrix_homeserver=optional(os.environ.get("MATRIX_HOMESERVER", "")),
        matrix_token=optional(os.environ.get("MATRIX_TOKEN", "")),
        matrix_room=optional(os.environ.get("MATRIX_ROOM", "")),
        persistent_notifications=os.environ.get("PERSISTENT_NOTIFICATIONS", "true") == "true",
    )


def _post_matrix(matrix_client, event, key, summary):
    # Best effort: the raw feed must never stop Jeeves tracking issues.
    if matrix_client is None:
        return
    try:
        matrix_client.post_issue(event, key, summary)
    except Exception as exc:
        print(f"[jeeves] matrix post failed for {key}: {exc}")


def run_poll_cycle(ha_client, ollama_client, store, config, matrix_client=None):
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()

    seen_keys = set()
    for watcher in WATCHERS:
        for issue in watcher(ha_client, ollama_client, store, config, now):
            seen_keys.add(issue.key)
            if not store.is_open(issue.key):
                if config.persistent_notifications:
                    ha_client.create_persistent_notification(issue.key, "Jeeves", issue.summary)
                _post_matrix(matrix_client, "open", issue.key, issue.summary)
            store.open_issue(issue.key, issue.summary, timestamp)

    for key in store.open_keys() - seen_keys:
        if config.persistent_notifications:
            ha_client.dismiss_persistent_notification(key)
        _post_matrix(matrix_client, "close", key, store.get_summary(key))
        store.close_issue(key)


def main():
    config = load_config()
    ha_client = HomeAssistantClient(config.ha_url, config.ha_token)
    ollama_client = (
        OllamaClient(config.ollama_url, config.ollama_model)
        if config.ollama_url
        else None
    )
    store = IssueStore("/share/jeeves_agent/jeeves.db")
    matrix_client = (
        MatrixClient(config.matrix_homeserver, config.matrix_token, config.matrix_room)
        if config.matrix_homeserver and config.matrix_token and config.matrix_room
        else None
    )

    interval_seconds = config.poll_interval_minutes * 60
    while True:
        try:
            run_poll_cycle(ha_client, ollama_client, store, config, matrix_client)
        except Exception as exc:
            print(f"[jeeves] poll cycle failed: {exc}")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
