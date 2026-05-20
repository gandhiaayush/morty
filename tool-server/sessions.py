import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_conn


def start_session(session_id: str, phone: str, role: str, started_at: str) -> dict:
    """Insert a new session row (silently ignored if session_id already exists)."""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO sessions (session_id, phone, role, started_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, phone, role, started_at),
        )
    return {"ok": True}


def list_sessions(limit: int = 20) -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return {"sessions": [dict(r) for r in rows]}


def end_session(session_id: str, ended_at: str, duration_sec: int | None) -> dict:
    """Mark a session as ended; returns an error dict if the session_id is unknown."""
    with get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE sessions
            SET ended_at = ?, duration_sec = ?
            WHERE session_id = ?
            """,
            (ended_at, duration_sec, session_id),
        )
        if cursor.rowcount == 0:
            return {"ok": False, "error": "session not found"}
    return {"ok": True}
