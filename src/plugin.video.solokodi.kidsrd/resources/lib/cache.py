import json
import os
import sqlite3
import time

try:
    import xbmcaddon
    import xbmcvfs

    def _get_cache_db_path():
        addon = xbmcaddon.Addon("plugin.video.solokodi.kidsrd")
        profile_path = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
        if not os.path.exists(profile_path):
            os.makedirs(profile_path, exist_ok=True)
        return os.path.join(profile_path, "cache.db")
except Exception:
    def _get_cache_db_path():
        tmp_dir = os.path.join(os.path.expanduser("~"), ".solokodi")
        os.makedirs(tmp_dir, exist_ok=True)
        return os.path.join(tmp_dir, "kidsrd_cache.db")


class SimpleCache:
    def __init__(self, db_path=None):
        self.db_path = db_path or _get_cache_db_path()
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS api_cache (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        expires_at REAL NOT NULL
                    )
                    """
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON api_cache(expires_at)")
        except Exception:
            pass

    def get(self, key):
        try:
            now = time.time()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value, expires_at FROM api_cache WHERE key = ?", (key,))
                row = cursor.fetchone()
                if row:
                    value, expires_at = row
                    if expires_at > now:
                        return json.loads(value)
                    else:
                        cursor.execute("DELETE FROM api_cache WHERE key = ?", (key,))
        except Exception:
            pass
        return None

    def set(self, key, value, ttl=3600):
        try:
            expires_at = time.time() + ttl
            serialized = json.dumps(value)
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO api_cache (key, value, expires_at)
                    VALUES (?, ?, ?)
                    """,
                    (key, serialized, expires_at),
                )
        except Exception:
            pass

    def delete(self, key):
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM api_cache WHERE key = ?", (key,))
        except Exception:
            pass

    def clear(self):
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM api_cache")
        except Exception:
            pass


cache = SimpleCache()
