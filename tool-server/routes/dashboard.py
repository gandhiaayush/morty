import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from datetime import datetime, timedelta
from database import get_conn


# ── shape helpers ─────────────────────────────────────────────────────────────

_STATUS = {"scheduled": "booked", "completed": "completed",
           "cancelled": "cancelled", "no_show": "cancelled"}


def _apt(row, customer=None) -> dict:
    d = {
        "id": row["id"],
        "customer_id": row["customer_id"],
        "service": row["service_name"] or "",
        "service_id": row["service_id"],
        "datetime": row["datetime"],
        "duration_min": row["duration_min"] if "duration_min" in row.keys() else 60,
        "status": _STATUS.get(row["status"], row["status"]),
        "reminder_sent": bool(row["reminder_sent"]),
    }
    if customer:
        d["customer"] = customer
    return d


def _svc(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "duration_min": row["duration_min"],
        "price": float(row["price"]),
        "active": bool(row["active"]),
    }


def _cust(row, created: bool = False) -> dict:
    d = {"id": row["id"], "name": row["name"], "phone": row["phone"]}
    if row["notes"]:
        d["notes"] = row["notes"]
    if created:
        d["created"] = True
    return d


# ── appointments ──────────────────────────────────────────────────────────────

def get_today_appointments() -> dict:
    today = datetime.now().date().isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT a.*, c.id AS cid, c.name AS cname, c.phone AS cphone,
                      c.notes AS cnotes, s.duration_min AS duration_min
               FROM appointments a
               LEFT JOIN customers c ON c.id = a.customer_id
               LEFT JOIN services s ON s.id = a.service_id
               WHERE date(a.datetime) = ? ORDER BY a.datetime ASC""",
            (today,),
        ).fetchall()
    results = []
    for r in rows:
        customer = {"id": r["cid"], "name": r["cname"], "phone": r["cphone"]}
        results.append(_apt(r, customer))
    return {"results": results}


def get_appointment_by_id(appointment_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            """SELECT a.*, c.id AS cid, c.name AS cname, c.phone AS cphone,
                      c.notes AS cnotes, s.duration_min AS duration_min
               FROM appointments a
               LEFT JOIN customers c ON c.id = a.customer_id
               LEFT JOIN services s ON s.id = a.service_id
               WHERE a.id = ?""",
            (appointment_id,),
        ).fetchone()
    if not row:
        return None
    customer = {"id": row["cid"], "name": row["cname"], "phone": row["cphone"]}
    return _apt(row, customer)


def search_dashboard(q: str) -> dict:
    results = []
    with get_conn() as conn:
        try:
            qid = int(q.strip())
            rows = conn.execute(
                """SELECT a.*, c.id AS cid, c.name AS cname, c.phone AS cphone,
                          c.notes AS cnotes, s.duration_min AS duration_min
                   FROM appointments a
                   LEFT JOIN customers c ON c.id = a.customer_id
                   LEFT JOIN services s ON s.id = a.service_id
                   WHERE a.id BETWEEN ? AND ?""",
                (qid - 2, qid + 2),
            ).fetchall()
        except ValueError:
            rows = conn.execute(
                """SELECT a.*, c.id AS cid, c.name AS cname, c.phone AS cphone,
                          c.notes AS cnotes, s.duration_min AS duration_min
                   FROM appointments a
                   LEFT JOIN customers c ON c.id = a.customer_id
                   LEFT JOIN services s ON s.id = a.service_id
                   WHERE c.name LIKE ? OR c.phone LIKE ?
                   ORDER BY a.datetime DESC""",
                (f"%{q}%", f"%{q}%"),
            ).fetchall()
        for r in rows:
            customer = {"id": r["cid"], "name": r["cname"], "phone": r["cphone"]}
            results.append(_apt(r, customer))
    return {"results": results}


def get_availability_slots(date: str, service_id: int | None = None) -> dict:
    duration_min = 60
    with get_conn() as conn:
        if service_id:
            svc = conn.execute(
                "SELECT duration_min FROM services WHERE id = ?", (service_id,)
            ).fetchone()
            if svc:
                duration_min = svc["duration_min"]

        day_start = datetime.fromisoformat(f"{date}T09:00:00")
        day_end = datetime.fromisoformat(f"{date}T19:00:00")
        booked_rows = conn.execute(
            "SELECT datetime FROM appointments WHERE datetime LIKE ? AND status != 'cancelled'",
            (f"{date}%",),
        ).fetchall()

    booked_starts = []
    for r in booked_rows:
        try:
            booked_starts.append(datetime.fromisoformat(r["datetime"]))
        except ValueError:
            pass

    open_slots = []
    slot = day_start
    while slot < day_end:
        slot_end = slot + timedelta(minutes=duration_min)
        overlap = any(bs < slot_end and slot < bs + timedelta(minutes=duration_min)
                      for bs in booked_starts)
        if not overlap:
            open_slots.append(slot.isoformat())
        slot += timedelta(minutes=30)

    return {"date": date, "open_slots": open_slots}


# ── book / modify / cancel ────────────────────────────────────────────────────

def book(customer_phone: str, service: str, dt: str,
         customer_name: str | None = None, duration_min: int | None = None) -> dict:
    with get_conn() as conn:
        cust = conn.execute(
            "SELECT * FROM customers WHERE phone = ?", (customer_phone,)
        ).fetchone()
        if cust:
            cust_id, cust_created = cust["id"], False
            cust_name = cust["name"]
        else:
            cust_name = customer_name or "Unknown"
            cur = conn.execute(
                "INSERT INTO customers (name, phone) VALUES (?, ?)", (cust_name, customer_phone)
            )
            cust_id, cust_created = cur.lastrowid, True

        svc = conn.execute(
            "SELECT * FROM services WHERE LOWER(name) LIKE LOWER(?)", (service,)
        ).fetchone()
        if svc:
            svc_id, svc_name, svc_dur = svc["id"], svc["name"], svc["duration_min"]
        else:
            svc_dur = duration_min or 60
            cur = conn.execute(
                "INSERT INTO services (name, duration_min, price) VALUES (?, ?, 0)", (service, svc_dur)
            )
            svc_id, svc_name = cur.lastrowid, service

        cur = conn.execute(
            """INSERT INTO appointments (customer_id, service_id, service_name, datetime, status)
               VALUES (?, ?, ?, ?, 'scheduled')""",
            (cust_id, svc_id, svc_name, dt),
        )
        apt_id = cur.lastrowid

    return {
        "appointment_id": apt_id,
        "status": "booked",
        "datetime": dt,
        "service": svc_name,
        "customer": {"id": cust_id, "name": cust_name, "phone": customer_phone,
                     **({"created": True} if cust_created else {})},
    }


def modify(appointment_id: int, changes: dict) -> dict:
    with get_conn() as conn:
        apt = conn.execute(
            "SELECT * FROM appointments WHERE id = ?", (appointment_id,)
        ).fetchone()
        if not apt:
            return {"success": False, "error": "Appointment not found"}

        fields, values, updated = [], [], []
        if "service" in changes and changes["service"]:
            svc = conn.execute(
                "SELECT * FROM services WHERE LOWER(name) LIKE LOWER(?)", (changes["service"],)
            ).fetchone()
            if svc:
                fields += ["service_id = ?", "service_name = ?"]
                values += [svc["id"], svc["name"]]
            else:
                fields.append("service_name = ?")
                values.append(changes["service"])
            updated.append("service")
        if "datetime" in changes and changes["datetime"]:
            fields.append("datetime = ?")
            values.append(changes["datetime"])
            updated.append("datetime")

        if fields:
            values.append(appointment_id)
            conn.execute(f"UPDATE appointments SET {', '.join(fields)} WHERE id = ?", values)

    return {"appointment_id": appointment_id, "status": "modified", "updated_fields": updated}


def cancel(appointment_id: int) -> dict:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE appointments SET status='cancelled' WHERE id=? AND status='scheduled'",
            (appointment_id,),
        )
        if cur.rowcount == 0:
            return {"success": False, "error": "Not found or already cancelled"}
    return {"appointment_id": appointment_id, "status": "cancelled"}


# ── customers ─────────────────────────────────────────────────────────────────

def get_customer_by_phone(phone: str, name: str | None = None) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM customers WHERE phone = ?", (phone,)).fetchone()
        if row:
            if name and name != row["name"]:
                conn.execute("UPDATE customers SET name=? WHERE id=?", (name, row["id"]))
                row = conn.execute("SELECT * FROM customers WHERE id=?", (row["id"],)).fetchone()
            return _cust(row)
        else:
            cur = conn.execute(
                "INSERT INTO customers (name, phone) VALUES (?, ?)", (name or "Unknown", phone)
            )
            row = conn.execute("SELECT * FROM customers WHERE id=?", (cur.lastrowid,)).fetchone()
            return _cust(row, created=True)


def update_customer(customer_id: int, name: str | None = None, notes: str | None = None) -> dict | None:
    with get_conn() as conn:
        fields, values = [], []
        if name is not None:
            fields.append("name=?"); values.append(name)
        if notes is not None:
            fields.append("notes=?"); values.append(notes)
        if fields:
            values.append(customer_id)
            conn.execute(f"UPDATE customers SET {', '.join(fields)} WHERE id=?", values)
        row = conn.execute("SELECT * FROM customers WHERE id=?", (customer_id,)).fetchone()
    return _cust(row) if row else None


# ── services ──────────────────────────────────────────────────────────────────

def get_services_list() -> list:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM services ORDER BY id ASC").fetchall()
    return [_svc(r) for r in rows]


def create_service(name: str, duration_min: int, price: float) -> dict:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO services (name, duration_min, price, active) VALUES (?, ?, ?, 1)",
            (name, duration_min, price),
        )
        row = conn.execute("SELECT * FROM services WHERE id=?", (cur.lastrowid,)).fetchone()
    return _svc(row)


def update_service_rest(service_id: int, name=None, duration_min=None, price=None, active=None) -> dict | None:
    with get_conn() as conn:
        fields, values = [], []
        if name is not None:
            fields.append("name=?"); values.append(name)
        if duration_min is not None:
            fields.append("duration_min=?"); values.append(duration_min)
        if price is not None:
            fields.append("price=?"); values.append(price)
        if active is not None:
            fields.append("active=?"); values.append(1 if active else 0)
        if fields:
            values.append(service_id)
            conn.execute(f"UPDATE services SET {', '.join(fields)} WHERE id=?", values)
        row = conn.execute("SELECT * FROM services WHERE id=?", (service_id,)).fetchone()
    return _svc(row) if row else None


def delete_service(service_id: int) -> dict:
    with get_conn() as conn:
        cur = conn.execute("UPDATE services SET active=0 WHERE id=?", (service_id,))
    return {"id": service_id, "deleted": cur.rowcount > 0}


def get_analytics(days: int = 30) -> dict:
    """
    Returns AnalyticsData matching this TypeScript interface:
    {
      total_booked: number
      total_revenue: number
      cancellation_rate: number
      daily_bookings: { date: string; count: number; revenue: number }[]
      busiest_slots: { hour: number; count: number }[]
    }
    """
    today = datetime.now().date()
    window_start = today - timedelta(days=days - 1)
    window_start_str = window_start.isoformat()
    window_end_str = today.isoformat()

    with get_conn() as conn:
        # total_booked: scheduled + completed in window
        row = conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM appointments
            WHERE status IN ('scheduled', 'completed')
              AND date(datetime) BETWEEN ? AND ?
            """,
            (window_start_str, window_end_str),
        ).fetchone()
        total_booked = row["cnt"] if row else 0

        # total_revenue: sum of service prices for completed appointments
        row = conn.execute(
            """
            SELECT COALESCE(SUM(s.price), 0.0) AS revenue
            FROM appointments a
            JOIN services s ON a.service_id = s.id
            WHERE a.status = 'completed'
              AND date(a.datetime) BETWEEN ? AND ?
            """,
            (window_start_str, window_end_str),
        ).fetchone()
        total_revenue = row["revenue"] if row else 0.0

        # cancellation_rate
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled
            FROM appointments
            WHERE date(datetime) BETWEEN ? AND ?
            """,
            (window_start_str, window_end_str),
        ).fetchone()
        if row and row["total"] and row["total"] > 0:
            cancellation_rate = round(row["cancelled"] / row["total"], 3)
        else:
            cancellation_rate = 0.0

        # daily_bookings: group by date for non-cancelled appointments
        rows = conn.execute(
            """
            SELECT
                date(a.datetime) AS appt_date,
                COUNT(*) AS cnt,
                COALESCE(SUM(CASE WHEN a.status = 'completed' THEN s.price ELSE 0 END), 0.0) AS revenue
            FROM appointments a
            LEFT JOIN services s ON a.service_id = s.id
            WHERE a.status != 'cancelled'
              AND date(a.datetime) BETWEEN ? AND ?
            GROUP BY date(a.datetime)
            """,
            (window_start_str, window_end_str),
        ).fetchall()

        # Build a lookup from the query results
        day_data = {r["appt_date"]: {"count": r["cnt"], "revenue": r["revenue"]} for r in rows}

        # Fill all days in the window, including gaps with zeros
        daily_bookings = []
        for i in range(days):
            d = (window_start + timedelta(days=i)).isoformat()
            entry = day_data.get(d, {"count": 0, "revenue": 0.0})
            daily_bookings.append({
                "date": d,
                "count": entry["count"],
                "revenue": float(entry["revenue"]),
            })

        # busiest_slots: top 9 hours by appointment count (non-cancelled)
        slot_rows = conn.execute(
            """
            SELECT
                CAST(strftime('%H', datetime) AS INTEGER) AS hour,
                COUNT(*) AS cnt
            FROM appointments
            WHERE status != 'cancelled'
              AND date(datetime) BETWEEN ? AND ?
            GROUP BY hour
            ORDER BY cnt DESC
            LIMIT 9
            """,
            (window_start_str, window_end_str),
        ).fetchall()

        busiest_slots = [{"hour": r["hour"], "count": r["cnt"]} for r in slot_rows]

    return {
        "total_booked": total_booked,
        "total_revenue": float(total_revenue),
        "cancellation_rate": cancellation_rate,
        "daily_bookings": daily_bookings,
        "busiest_slots": busiest_slots,
    }
