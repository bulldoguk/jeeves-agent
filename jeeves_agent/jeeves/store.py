import sqlite3


class IssueStore:
    """Tracks open issues so we notify on new/resolved state changes only,
    not on every poll cycle."""

    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS issues (
                key TEXT PRIMARY KEY,
                summary TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def get_meta(self, key, default=""):
        row = self.conn.execute(
            "SELECT value FROM metadata WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else default

    def set_meta(self, key, value):
        self.conn.execute(
            """
            INSERT INTO metadata (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, str(value)),
        )
        self.conn.commit()

    def is_open(self, key):
        row = self.conn.execute(
            "SELECT 1 FROM issues WHERE key = ?", (key,)
        ).fetchone()
        return row is not None

    def open_issue(self, key, summary, timestamp):
        self.conn.execute(
            """
            INSERT INTO issues (key, summary, first_seen, last_seen)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET last_seen = excluded.last_seen
            """,
            (key, summary, timestamp, timestamp),
        )
        self.conn.commit()

    def close_issue(self, key):
        self.conn.execute("DELETE FROM issues WHERE key = ?", (key,))
        self.conn.commit()

    def open_keys(self):
        rows = self.conn.execute("SELECT key FROM issues").fetchall()
        return {row[0] for row in rows}
