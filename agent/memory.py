"""
NaraTask AI - Memory Manager
SQLite-based persistence for conversations, facts, and reminders.
"""

import json
import logging
from datetime import datetime
from typing import Optional
import aiosqlite

from config import DB_PATH

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Manages persistent memory using SQLite.
    Stores conversations, user facts, and reminders.
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self.db = None

    async def initialize(self):
        """Initialize database connection and create tables."""
        self.db = await aiosqlite.connect(self.db_path)
        await self._create_tables()
        logger.info(f"Memory database initialized at {self.db_path}")

    async def close(self):
        """Close database connection."""
        if self.db:
            await self.db.close()

    async def _create_tables(self):
        """Create database tables if they don't exist."""
        await self.db.executescript("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_calls TEXT,
                tool_results TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                trigger_at TIMESTAMP NOT NULL,
                is_triggered BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS task_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                input_params TEXT,
                output_result TEXT,
                status TEXT NOT NULL,
                duration_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_reminders_trigger ON reminders(trigger_at, is_triggered);
            CREATE INDEX IF NOT EXISTS idx_task_log_session ON task_log(session_id);
        """)
        await self.db.commit()

    # ----- Message Operations -----

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[list] = None,
        tool_results: Optional[list] = None
    ):
        """Add a message to conversation history."""
        await self.db.execute(
            """INSERT INTO messages (session_id, role, content, tool_calls, tool_results)
               VALUES (?, ?, ?, ?, ?)""",
            (
                session_id,
                role,
                content,
                json.dumps(tool_calls) if tool_calls else None,
                json.dumps(tool_results) if tool_results else None
            )
        )
        await self.db.commit()

    async def get_messages(
        self,
        session_id: str,
        limit: int = 50
    ) -> list[dict]:
        """Get conversation history for a session."""
        cursor = await self.db.execute(
            """SELECT role, content, tool_calls, tool_results, created_at
               FROM messages
               WHERE session_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (session_id, limit)
        )
        rows = await cursor.fetchall()

        messages = []
        for row in reversed(rows):
            msg = {
                "role": row[0],
                "content": row[1],
                "created_at": row[4]
            }
            if row[2]:
                msg["tool_calls"] = json.loads(row[2])
            if row[3]:
                msg["tool_results"] = json.loads(row[3])
            messages.append(msg)

        return messages

    async def get_messages_for_llm(
        self,
        session_id: str,
        limit: int = 20
    ) -> list[dict]:
        """Get messages formatted for LLM API."""
        messages = await self.get_messages(session_id, limit)

        llm_messages = []
        for msg in messages:
            llm_msg = {"role": msg["role"], "content": msg["content"]}

            # Add tool calls if present
            if "tool_calls" in msg and msg["tool_calls"]:
                llm_msg["tool_calls"] = msg["tool_calls"]

            # Add tool results if present
            if "tool_results" in msg and msg["tool_results"]:
                for result in msg["tool_results"]:
                    llm_messages.append({
                        "role": "tool",
                        "tool_call_id": result["tool_call_id"],
                        "content": result["content"]
                    })

            llm_messages.append(llm_msg)

        return llm_messages

    async def clear_session(self, session_id: str):
        """Clear all messages for a session."""
        await self.db.execute(
            "DELETE FROM messages WHERE session_id = ?",
            (session_id,)
        )
        await self.db.commit()

    async def get_sessions(self) -> list[dict]:
        """Get list of all sessions with metadata."""
        cursor = await self.db.execute(
            """SELECT session_id,
                      MIN(created_at) as started,
                      MAX(created_at) as last_active,
                      COUNT(*) as message_count
               FROM messages
               GROUP BY session_id
               ORDER BY last_active DESC"""
        )
        rows = await cursor.fetchall()

        return [
            {
                "session_id": row[0],
                "started": row[1],
                "last_active": row[2],
                "message_count": row[3]
            }
            for row in rows
        ]

    # ----- Facts Operations -----

    async def save_fact(self, key: str, value: str):
        """Save or update a user fact/preference."""
        await self.db.execute(
            """INSERT INTO facts (key, value, updated_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(key) DO UPDATE SET
               value = excluded.value,
               updated_at = CURRENT_TIMESTAMP""",
            (key, value)
        )
        await self.db.commit()

    async def get_fact(self, key: str) -> Optional[str]:
        """Get a specific fact by key."""
        cursor = await self.db.execute(
            "SELECT value FROM facts WHERE key = ?",
            (key,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None

    async def get_all_facts(self) -> dict:
        """Get all stored facts."""
        cursor = await self.db.execute("SELECT key, value FROM facts")
        rows = await cursor.fetchall()
        return {row[0]: row[1] for row in rows}

    async def delete_fact(self, key: str):
        """Delete a fact."""
        await self.db.execute("DELETE FROM facts WHERE key = ?", (key,))
        await self.db.commit()

    # ----- Reminder Operations -----

    async def add_reminder(self, message: str, trigger_at: datetime) -> int:
        """Add a new reminder."""
        cursor = await self.db.execute(
            "INSERT INTO reminders (message, trigger_at) VALUES (?, ?)",
            (message, trigger_at.isoformat())
        )
        await self.db.commit()
        return cursor.lastrowid

    async def get_pending_reminders(self) -> list[dict]:
        """Get all reminders that should have triggered."""
        cursor = await self.db.execute(
            """SELECT id, message, trigger_at
               FROM reminders
               WHERE is_triggered = FALSE
               AND trigger_at <= CURRENT_TIMESTAMP
               ORDER BY trigger_at"""
        )
        rows = await cursor.fetchall()

        return [
            {
                "id": row[0],
                "message": row[1],
                "trigger_at": row[2]
            }
            for row in rows
        ]

    async def mark_reminder_triggered(self, reminder_id: int):
        """Mark a reminder as triggered."""
        await self.db.execute(
            "UPDATE reminders SET is_triggered = TRUE WHERE id = ?",
            (reminder_id,)
        )
        await self.db.commit()

    async def get_active_reminders(self) -> list[dict]:
        """Get all active (non-triggered) reminders."""
        cursor = await self.db.execute(
            """SELECT id, message, trigger_at, created_at
               FROM reminders
               WHERE is_triggered = FALSE
               ORDER BY trigger_at"""
        )
        rows = await cursor.fetchall()

        return [
            {
                "id": row[0],
                "message": row[1],
                "trigger_at": row[2],
                "created_at": row[3]
            }
            for row in rows
        ]

    async def delete_reminder(self, reminder_id: int):
        """Delete a reminder."""
        await self.db.execute(
            "DELETE FROM reminders WHERE id = ?",
            (reminder_id,)
        )
        await self.db.commit()

    # ----- Task Log Operations -----

    async def log_task(
        self,
        session_id: str,
        tool_name: str,
        input_params: dict,
        output_result: dict,
        status: str,
        duration_ms: int
    ):
        """Log a tool execution."""
        await self.db.execute(
            """INSERT INTO task_log
               (session_id, tool_name, input_params, output_result, status, duration_ms)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                tool_name,
                json.dumps(input_params),
                json.dumps(output_result),
                status,
                duration_ms
            )
        )
        await self.db.commit()

    async def get_task_stats(self, session_id: Optional[str] = None) -> dict:
        """Get task execution statistics."""
        query = """
            SELECT
                tool_name,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                AVG(duration_ms) as avg_duration
            FROM task_log
        """
        params = []

        if session_id:
            query += " WHERE session_id = ?"
            params.append(session_id)

        query += " GROUP BY tool_name"

        cursor = await self.db.execute(query, params)
        rows = await cursor.fetchall()

        return {
            row[0]: {
                "total": row[1],
                "success": row[2],
                "avg_duration_ms": row[3]
            }
            for row in rows
        }