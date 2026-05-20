import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_conn
from models import BookAppointmentRequest, ModifyAppointmentRequest, CancelAppointmentRequest


def book_appointment(req: BookAppointmentRequest) -> dict:
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT id, name, phone, notes FROM customers WHERE phone = ?",
                (req.customer_phone,),
            ).fetchone()

            if row:
                customer_id = row["id"]
            else:
                name = req.customer_name or "Unknown"
                cur = conn.execute(
                    "INSERT INTO customers (name, phone) VALUES (?, ?)",
                    (name, req.customer_phone),
                )
                customer_id = cur.lastrowid

            svc = conn.execute(
                "SELECT id, name, duration_min, price FROM services WHERE LOWER(name) LIKE LOWER(?)",
                (req.service_name,),
            ).fetchone()

            if svc:
                service_id = svc["id"]
                service_name = svc["name"]
            else:
                cur = conn.execute(
                    "INSERT INTO services (name, duration_min, price) VALUES (?, 60, 0)",
                    (req.service_name,),
                )
                service_id = cur.lastrowid
                service_name = req.service_name

            cur = conn.execute(
                """INSERT INTO appointments (customer_id, service_id, service_name, datetime, status, notes)
                   VALUES (?, ?, ?, ?, 'scheduled', ?)""",
                (customer_id, service_id, service_name, req.datetime, req.notes),
            )
            appt_id = cur.lastrowid
            conn.commit()

            appt = conn.execute(
                "SELECT * FROM appointments WHERE id = ?", (appt_id,)
            ).fetchone()

            return {"success": True, "appointment": dict(appt)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def modify_appointment(req: ModifyAppointmentRequest) -> dict:
    try:
        with get_conn() as conn:
            appt = conn.execute(
                "SELECT * FROM appointments WHERE id = ?", (req.appointment_id,)
            ).fetchone()

            if not appt:
                return {"success": False, "error": "Appointment not found"}

            if appt["status"] != "scheduled":
                return {
                    "success": False,
                    "error": f"Appointment cannot be modified (status: {appt['status']})",
                }

            fields = []
            values = []

            if req.service_name is not None:
                svc = conn.execute(
                    "SELECT id, name FROM services WHERE LOWER(name) LIKE LOWER(?)",
                    (req.service_name,),
                ).fetchone()
                if svc:
                    fields.append("service_id = ?")
                    values.append(svc["id"])
                    fields.append("service_name = ?")
                    values.append(svc["name"])
                else:
                    cur = conn.execute(
                        "INSERT INTO services (name, duration_min, price) VALUES (?, 60, 0)",
                        (req.service_name,),
                    )
                    fields.append("service_id = ?")
                    values.append(cur.lastrowid)
                    fields.append("service_name = ?")
                    values.append(req.service_name)

            if req.datetime is not None:
                fields.append("datetime = ?")
                values.append(req.datetime)

            if req.notes is not None:
                fields.append("notes = ?")
                values.append(req.notes)

            if fields:
                values.append(req.appointment_id)
                conn.execute(
                    f"UPDATE appointments SET {', '.join(fields)} WHERE id = ?",
                    values,
                )
                conn.commit()

            appt = conn.execute(
                "SELECT * FROM appointments WHERE id = ?", (req.appointment_id,)
            ).fetchone()

            return {"success": True, "appointment": dict(appt)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_appointments(date: str | None = None, status: str | None = None) -> dict:
    try:
        with get_conn() as conn:
            query = """
                SELECT a.*, c.name AS customer_name, c.phone AS customer_phone
                FROM appointments a
                LEFT JOIN customers c ON c.id = a.customer_id
                WHERE 1=1
            """
            params: list = []
            if date:
                query += " AND a.datetime LIKE ?"
                params.append(f"{date}%")
            if status:
                query += " AND a.status = ?"
                params.append(status)
            query += " ORDER BY a.datetime ASC"
            rows = conn.execute(query, params).fetchall()
        return {"appointments": [dict(r) for r in rows]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def update_service(
    service_id: int,
    name: str | None = None,
    duration_min: int | None = None,
    price: float | None = None,
) -> dict:
    try:
        with get_conn() as conn:
            fields, values = [], []
            if name is not None:
                fields.append("name = ?")
                values.append(name)
            if duration_min is not None:
                fields.append("duration_min = ?")
                values.append(duration_min)
            if price is not None:
                fields.append("price = ?")
                values.append(price)
            if not fields:
                return {"success": False, "error": "No fields to update"}
            values.append(service_id)
            cur = conn.execute(
                f"UPDATE services SET {', '.join(fields)} WHERE id = ?", values
            )
            if cur.rowcount == 0:
                return {"success": False, "error": "Service not found"}
            svc = conn.execute("SELECT * FROM services WHERE id = ?", (service_id,)).fetchone()
        return {"success": True, "service": dict(svc)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def cancel_appointment(req: CancelAppointmentRequest) -> dict:
    try:
        with get_conn() as conn:
            cur = conn.execute(
                "UPDATE appointments SET status = 'cancelled' WHERE id = ? AND status = 'scheduled'",
                (req.appointment_id,),
            )
            conn.commit()

            if cur.rowcount == 0:
                return {
                    "success": False,
                    "error": "Appointment not found or already cancelled",
                }

            return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
