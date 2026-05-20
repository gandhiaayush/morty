import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "salon.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS customers (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT NOT NULL,
                phone   TEXT UNIQUE NOT NULL,
                notes   TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS services (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT NOT NULL,
                duration_min INTEGER NOT NULL DEFAULT 60,
                price        REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS appointments (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id   INTEGER NOT NULL,
                service_id    INTEGER,
                service_name  TEXT,
                datetime      TEXT NOT NULL,
                status        TEXT DEFAULT 'scheduled',
                notes         TEXT,
                reminder_sent INTEGER DEFAULT 0,
                created_at    TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            );

            INSERT OR IGNORE INTO services (id, name, duration_min, price) VALUES
                (1, 'Manicure',         45, 35),
                (2, 'Pedicure',         60, 50),
                (3, 'Gel Manicure',     60, 50),
                (4, 'Gel Pedicure',     75, 65),
                (5, 'Full Set Acrylic', 90, 70),
                (6, 'Fill',             60, 45),
                (7, 'Nail Art',         30, 25);

            CREATE TABLE IF NOT EXISTS sessions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   TEXT UNIQUE NOT NULL,
                phone        TEXT NOT NULL,
                role         TEXT NOT NULL DEFAULT 'consumer',
                started_at   TEXT NOT NULL,
                ended_at     TEXT,
                duration_sec INTEGER,
                created_at   TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS callbacks (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                appointment_id  INTEGER NOT NULL,
                triggered_at    TEXT NOT NULL,
                twilio_call_sid TEXT,
                status          TEXT DEFAULT 'pending',
                FOREIGN KEY (appointment_id) REFERENCES appointments(id)
            );
        """)
