import sqlite3
import hashlib
import json
from typing import Optional

class CacheMCP:
    def __init__(self, path="cache/cache.db"):
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            payload TEXT
        )
        """)

    def _key(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def get(self, text: str) -> Optional[dict]:
        key = self._key(text)
        row = self.conn.execute(
            "SELECT payload FROM cache WHERE key=?", (key,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def set(self, text: str, payload: dict):
        key = self._key(text)
        self.conn.execute(
            "INSERT OR REPLACE INTO cache VALUES (?,?)",
            (key, json.dumps(payload))
        )
        self.conn.commit()
