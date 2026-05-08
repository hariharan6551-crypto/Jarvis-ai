"""
J.A.R.V.I.S Memory Engine
SQLite for conversation history + ChromaDB for vector memory search.
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from core.logger import get_logger
from config.settings import settings

log = get_logger("memory")


class MemoryEngine:
    """Manages conversation history and vector memory."""

    def __init__(self):
        self.db_path = settings.SQLITE_DB_PATH
        self._init_sqlite()
        self._init_chroma()
        log.info("Memory engine initialized")

    def _init_sqlite(self):
        """Initialize SQLite database with schema."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                title TEXT,
                summary TEXT
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );

            CREATE TABLE IF NOT EXISTS commands (
                id TEXT PRIMARY KEY,
                command TEXT NOT NULL,
                intent TEXT,
                status TEXT DEFAULT 'pending',
                result TEXT,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration_ms REAL
            );

            CREATE TABLE IF NOT EXISTS system_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
            CREATE INDEX IF NOT EXISTS idx_commands_status ON commands(status);
        """)

        conn.commit()
        conn.close()
        log.debug("SQLite database initialized")

    def _init_chroma(self):
        """Initialize ChromaDB for vector memory."""
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self.chroma_client = chromadb.Client(
                ChromaSettings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=settings.CHROMA_DB_PATH,
                    anonymized_telemetry=False,
                )
            )
            self.memory_collection = self.chroma_client.get_or_create_collection(
                name="jarvis_memory",
                metadata={"hnsw:space": "cosine"},
            )
            log.debug("ChromaDB initialized")
        except Exception as e:
            log.warning(f"ChromaDB initialization failed (non-critical): {e}")
            self.chroma_client = None
            self.memory_collection = None

    def create_conversation(self, title: str = "New Conversation") -> str:
        """Create a new conversation and return its ID."""
        conv_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO conversations (id, title) VALUES (?, ?)",
            (conv_id, title),
        )
        conn.commit()
        conn.close()
        return conv_id

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> str:
        """Add a message to conversation history."""
        msg_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO messages (id, conversation_id, role, content, metadata) VALUES (?, ?, ?, ?, ?)",
            (msg_id, conversation_id, role, content, json.dumps(metadata or {})),
        )
        conn.commit()
        conn.close()

        # Store in vector memory for semantic search
        if self.memory_collection:
            try:
                self.memory_collection.add(
                    documents=[content],
                    metadatas=[{"role": role, "conversation_id": conversation_id}],
                    ids=[msg_id],
                )
            except Exception as e:
                log.debug(f"Vector memory add failed: {e}")

        return msg_id

    def get_conversation_history(
        self, conversation_id: str, limit: int = 50
    ) -> list:
        """Retrieve conversation history."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp DESC LIMIT ?",
            (conversation_id, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in reversed(rows)]

    def get_recent_messages(self, limit: int = 20) -> list:
        """Get recent messages across all conversations."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM messages ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in reversed(rows)]

    def search_memory(self, query: str, n_results: int = 5) -> list:
        """Semantic search across memory using ChromaDB."""
        if not self.memory_collection:
            return []
        try:
            results = self.memory_collection.query(
                query_texts=[query], n_results=n_results
            )
            return results.get("documents", [[]])[0]
        except Exception as e:
            log.error(f"Memory search failed: {e}")
            return []

    def log_command(
        self, command: str, intent: str, status: str = "pending", result: str = None, duration_ms: float = None
    ) -> str:
        """Log a command execution."""
        cmd_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO commands (id, command, intent, status, result, duration_ms) VALUES (?, ?, ?, ?, ?, ?)",
            (cmd_id, command, intent, status, result, duration_ms),
        )
        conn.commit()
        conn.close()
        return cmd_id

    def log_event(self, event_type: str, details: str = None):
        """Log a system event."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO system_events (event_type, details) VALUES (?, ?)",
            (event_type, details),
        )
        conn.commit()
        conn.close()

    def get_stats(self) -> dict:
        """Get memory statistics."""
        conn = sqlite3.connect(self.db_path)
        stats = {
            "total_conversations": conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0],
            "total_messages": conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0],
            "total_commands": conn.execute("SELECT COUNT(*) FROM commands").fetchone()[0],
            "successful_commands": conn.execute(
                "SELECT COUNT(*) FROM commands WHERE status = 'success'"
            ).fetchone()[0],
        }
        conn.close()
        return stats
