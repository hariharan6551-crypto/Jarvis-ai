"""
J.A.R.V.I.S User Preference Learning Engine
Remembers user habits, frequently used apps, accounts, and command patterns.
"""

import json
import sqlite3
import time
from pathlib import Path
from collections import Counter
from core.logger import get_logger
from config.settings import settings

log = get_logger("preferences")


class PreferenceEngine:
    """Learns and remembers user preferences and patterns."""

    def __init__(self):
        self.db_path = settings.SQLITE_DB_PATH
        self._init_tables()
        log.info("Preference engine initialized")

    def _init_tables(self):
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS app_usage (
                app_name TEXT NOT NULL,
                count INTEGER DEFAULT 1,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                profile TEXT DEFAULT NULL
            );
            CREATE TABLE IF NOT EXISTS command_patterns (
                pattern TEXT PRIMARY KEY,
                frequency INTEGER DEFAULT 1,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                avg_duration_ms REAL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS learned_shortcuts (
                trigger_phrase TEXT PRIMARY KEY,
                action_plan TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                use_count INTEGER DEFAULT 0
            );
        """)
        conn.commit()
        conn.close()

    # ─── Preferences ──────────────────────────────────────────────────

    def set_preference(self, key: str, value: str, category: str = "general"):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO user_preferences (key, value, category, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (key, value, category)
        )
        conn.commit()
        conn.close()

    def get_preference(self, key: str, default=None) -> str:
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT value FROM user_preferences WHERE key = ?", (key,)).fetchone()
        conn.close()
        return row[0] if row else default

    def get_all_preferences(self, category: str = None) -> dict:
        conn = sqlite3.connect(self.db_path)
        if category:
            rows = conn.execute("SELECT key, value FROM user_preferences WHERE category = ?", (category,)).fetchall()
        else:
            rows = conn.execute("SELECT key, value FROM user_preferences").fetchall()
        conn.close()
        return {k: v for k, v in rows}

    # ─── App Usage Tracking ───────────────────────────────────────────

    def track_app_usage(self, app_name: str, profile: str = None):
        conn = sqlite3.connect(self.db_path)
        existing = conn.execute(
            "SELECT count FROM app_usage WHERE app_name = ? AND (profile = ? OR (profile IS NULL AND ? IS NULL))",
            (app_name, profile, profile)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE app_usage SET count = count + 1, last_used = CURRENT_TIMESTAMP WHERE app_name = ? AND (profile = ? OR (profile IS NULL AND ? IS NULL))",
                (app_name, profile, profile)
            )
        else:
            conn.execute("INSERT INTO app_usage (app_name, profile) VALUES (?, ?)", (app_name, profile))
        conn.commit()
        conn.close()

    def get_frequent_apps(self, limit: int = 10) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT app_name, profile, count, last_used FROM app_usage ORDER BY count DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_preferred_profile(self, app_name: str) -> str:
        """Get the most-used profile for an app (e.g., Chrome)."""
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT profile FROM app_usage WHERE app_name = ? AND profile IS NOT NULL ORDER BY count DESC LIMIT 1",
            (app_name,)
        ).fetchone()
        conn.close()
        return row[0] if row else None

    # ─── Command Patterns ─────────────────────────────────────────────

    def track_command(self, pattern: str, duration_ms: float = 0):
        conn = sqlite3.connect(self.db_path)
        existing = conn.execute("SELECT frequency, avg_duration_ms FROM command_patterns WHERE pattern = ?", (pattern,)).fetchone()
        if existing:
            freq = existing[0] + 1
            avg = ((existing[1] * existing[0]) + duration_ms) / freq
            conn.execute(
                "UPDATE command_patterns SET frequency = ?, avg_duration_ms = ?, last_used = CURRENT_TIMESTAMP WHERE pattern = ?",
                (freq, avg, pattern)
            )
        else:
            conn.execute("INSERT INTO command_patterns (pattern, avg_duration_ms) VALUES (?, ?)", (pattern, duration_ms))
        conn.commit()
        conn.close()

    def get_frequent_commands(self, limit: int = 10) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT pattern, frequency, last_used FROM command_patterns ORDER BY frequency DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ─── Learned Shortcuts ────────────────────────────────────────────

    def learn_shortcut(self, trigger: str, action_plan: list[dict]):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO learned_shortcuts (trigger_phrase, action_plan) VALUES (?, ?)",
            (trigger.lower(), json.dumps(action_plan))
        )
        conn.commit()
        conn.close()
        log.info(f"Learned shortcut: '{trigger}'")

    def find_shortcut(self, text: str) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT action_plan FROM learned_shortcuts WHERE trigger_phrase = ?",
            (text.lower(),)
        ).fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
        return None

    def get_user_context(self) -> dict:
        """Get a summary of user preferences for AI context."""
        return {
            "frequent_apps": self.get_frequent_apps(5),
            "frequent_commands": self.get_frequent_commands(5),
            "preferences": self.get_all_preferences(),
        }
