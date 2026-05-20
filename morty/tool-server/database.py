import sqlite3
import os
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", "morty.db")


def _open_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_db():
    conn = _open_db()
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    conn = _open_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            price_cents INTEGER NOT NULL,
            duration_minutes INTEGER NOT NULL DEFAULT 60,
            description TEXT
        );
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            color_name TEXT NOT NULL,
            brand TEXT,
            hex_code TEXT,
            quantity INTEGER DEFAULT 1,
            in_stock INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            service_id INTEGER NOT NULL REFERENCES services(id),
            nail_color TEXT,
            datetime TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            reminder_sent_at TEXT,
            call_sid TEXT
        );
        CREATE TABLE IF NOT EXISTS callbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER REFERENCES customers(id),
            phone TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            attempts INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            resolved_at TEXT
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_sid TEXT NOT NULL UNIQUE,
            phone TEXT,
            role TEXT DEFAULT 'consumer',
            started_at TEXT DEFAULT (datetime('now')),
            ended_at TEXT,
            actions_taken TEXT DEFAULT '[]'
        );
    """)
    conn.commit()
    conn.close()
