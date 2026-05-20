import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from database import get_conn


def get_or_create_customer(phone: str, name: str | None = None) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, phone, notes FROM customers WHERE phone = ?",
            (phone,),
        ).fetchone()

        if row:
            if name and name != row["name"]:
                conn.execute(
                    "UPDATE customers SET name = ? WHERE id = ?",
                    (name, row["id"]),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT id, name, phone, notes FROM customers WHERE id = ?",
                    (row["id"],),
                ).fetchone()
        else:
            cur = conn.execute(
                "INSERT INTO customers (name, phone) VALUES (?, ?)",
                (name or "Unknown", phone),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id, name, phone, notes FROM customers WHERE id = ?",
                (cur.lastrowid,),
            ).fetchone()

        return {"customer": dict(row)}


def get_services() -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT name, duration_min, price FROM services ORDER BY price ASC"
        ).fetchall()
    return {"services": [dict(r) for r in rows]}


def get_availability(date: str, service_name: str | None = None) -> list[dict]:
    duration_min = 60

    with get_conn() as conn:
        if service_name:
            svc = conn.execute(
                "SELECT duration_min FROM services WHERE LOWER(name) LIKE LOWER(?)",
                (service_name,),
            ).fetchone()
            if svc:
                duration_min = svc["duration_min"]

        day_start = datetime.fromisoformat(f"{date}T09:00:00")
        day_end = datetime.fromisoformat(f"{date}T19:00:00")

        slots = []
        current = day_start
        while current < day_end:
            slots.append(current)
            current += timedelta(minutes=30)

        date_prefix = f"{date}%"
        appts = conn.execute(
            "SELECT datetime FROM appointments WHERE datetime LIKE ? AND status = 'scheduled'",
            (date_prefix,),
        ).fetchall()

        booked_starts = []
        for appt in appts:
            try:
                booked_starts.append(datetime.fromisoformat(appt["datetime"]))
            except ValueError:
                pass

        results = []
        for slot in slots:
            slot_end = slot + timedelta(minutes=duration_min)
            overlap = False
            for bs in booked_starts:
                bs_end = bs + timedelta(minutes=duration_min)
                if bs < slot_end and slot < bs_end:
                    overlap = True
                    break

            results.append({"slot": slot.strftime("%H:%M"), "available": not overlap})

    return results
