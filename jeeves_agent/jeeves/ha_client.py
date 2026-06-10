import requests
from datetime import datetime, timedelta, timezone


class HomeAssistantClient:
    """Thin wrapper around the HA REST API — read-only plus notify."""

    def __init__(self, base_url, token):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def get_state(self, entity_id):
        resp = requests.get(
            f"{self.base_url}/api/states/{entity_id}",
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def get_history(self, entity_id, hours=24):
        start = datetime.now(timezone.utc) - timedelta(hours=hours)
        resp = requests.get(
            f"{self.base_url}/api/history/period/{start.isoformat()}",
            headers=self.headers,
            params={"filter_entity_id": entity_id},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data[0] if data else []

    def notify(self, notify_target, title, message):
        service = notify_target.split(".", 1)[-1]
        resp = requests.post(
            f"{self.base_url}/api/services/notify/{service}",
            headers=self.headers,
            json={"title": title, "message": message},
            timeout=10,
        )
        resp.raise_for_status()
