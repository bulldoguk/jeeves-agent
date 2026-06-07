import os
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field

from jeeves.ha_client import HomeAssistantClient
from jeeves.store import IssueStore
from jeeves.watchers import WATCHERS


@dataclass
class Config:
    ha_url: str
    ha_token: str
    notify_target: str
    poll_interval_minutes: int
    watch_temperature_entities: list = field(default_factory=list)
    watch_camera_entities: list = field(default_factory=list)


def load_config():
    def split_entities(value):
        return [e.strip() for e in value.split(",") if e.strip()]

    return Config(
        ha_url=os.environ["HA_URL"],
        ha_token=os.environ["HA_TOKEN"],
        notify_target=os.environ.get("NOTIFY_TARGET", "notify.notify"),
        poll_interval_minutes=int(os.environ.get("POLL_INTERVAL_MINUTES", "5")),
        watch_temperature_entities=split_entities(
            os.environ.get("WATCH_TEMPERATURE_ENTITIES", "")
        ),
        watch_camera_entities=split_entities(
            os.environ.get("WATCH_CAMERA_ENTITIES", "")
        ),
    )


def run_poll_cycle(ha_client, store, config):
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()

    seen_keys = set()
    for watcher in WATCHERS:
        for issue in watcher(ha_client, config, now):
            seen_keys.add(issue.key)
            if not store.is_open(issue.key):
                ha_client.notify(config.notify_target, "Jeeves: issue detected", issue.summary)
            store.open_issue(issue.key, issue.summary, timestamp)

    for key in store.open_keys() - seen_keys:
        ha_client.notify(config.notify_target, "Jeeves: resolved", f"No longer an issue: {key}")
        store.close_issue(key)


def main():
    config = load_config()
    ha_client = HomeAssistantClient(config.ha_url, config.ha_token)
    store = IssueStore("/share/jeeves_agent/jeeves.db")

    interval_seconds = config.poll_interval_minutes * 60
    while True:
        try:
            run_poll_cycle(ha_client, store, config)
        except Exception as exc:
            print(f"[jeeves] poll cycle failed: {exc}")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
