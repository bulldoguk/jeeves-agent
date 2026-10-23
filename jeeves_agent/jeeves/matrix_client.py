import uuid
from urllib.parse import quote

import requests

# Machine-readable payload key shared by every agent on the agent-messaging bus.
# `body` is for people; this dict is what other agents act on.
AGENT_KEY = "org.myhmbiz.agent"


class MatrixClient:
    """Posts issue opens and closes to one Matrix room (the raw feed that the
    triage agent filters). Unencrypted room, so plain HTTP is enough."""

    def __init__(self, homeserver, token, room_id):
        self.url = (
            f"{homeserver.rstrip('/')}/_matrix/client/v3/rooms/"
            f"{quote(room_id, safe='')}/send/m.room.message/"
        )
        self.headers = {"Authorization": f"Bearer {token}"}

    def post_issue(self, event, key, summary):
        icon = "🔴" if event == "open" else "✅"
        content = {
            "msgtype": "m.notice",
            "body": f"{icon} {event}: {summary}",
            AGENT_KEY: {"source": "jeeves", "event": event, "key": key, "summary": summary},
        }
        resp = requests.put(self.url + uuid.uuid4().hex, headers=self.headers, json=content, timeout=10)
        resp.raise_for_status()
