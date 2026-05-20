from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3
from datetime import date, datetime, timedelta

from database import get_db
from tools.customers import normalize_phone

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _appointment_row_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "customer_name": row["customer_name"],
        "phone": row["phone"],
        "service_name": row["service_name"],
        "service_price_dollars": row["price_cents"] / 100.0,
        "nail_color": row["nail_color"],
        "datetime": row["datetime"],
        "status": row["status"],
        "notes": row["notes"],
    }


def _upcoming_appointments(db: sqlite3.Connection, customer_id: int) -> list:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = db.execute(
        """
        SELECT a.id, c.name AS customer_name, c.phone, s.name AS service_name,
               s.price_cents, a.nail_color, a.datetime, a.status, a.notes
        FROM appointments a
        JOIN customers c ON c.id = a.customer_id
        JOIN services s ON s.id = a.service_id
        WHERE a.customer_id = ?
          AND a.status IN ('Pending', 'Confirmed')
          AND a.datetime >= ?
        ORDER BY a.datetime
        """,
        (customer_id, now),
    ).fetchall()
    return [_appointment_row_to_dict(r) for r in rows]


def _customer_row_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "phone": row["phone"],
        "created_at": row["created_at"],
    }


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SearchCustomerRequest(BaseModel):
    phone: Optional[str] = None
    name: Optional[str] = None


class GetAppointmentRequest(BaseModel):
    appointment_id: int


class ListAvailableSlotsRequest(BaseModel):
    date: str  # YYYY-MM-DD
    service_name: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/search_customer")
def search_customer(body: SearchCustomerRequest, db: sqlite3.Connection = Depends(get_db)):
    customer_row = None

    if body.phone:
        normalized = normalize_phone(body.phone)
        customer_row = db.execute(
            "SELECT id, name, phone, created_at FROM customers WHERE phone = ?",
            (normalized,),
        ).fetchone()

    if customer_row is None and body.name:
        customer_row = db.execute(
            "SELECT id, name, phone, created_at FROM customers WHERE LOWER(name) LIKE LOWER(?)",
            (f"%{body.name}%",),
        ).fetchone()

    if customer_row is None:
        return {"found": False, "customer": None, "upcoming_appointments": []}

    customer = _customer_row_to_dict(customer_row)
    upcoming = _upcoming_appointments(db, customer_row["id"])
    return {"found": True, "customer": customer, "upcoming_appointments": upcoming}


@router.post("/get_appointment")
def get_appointment(body: GetAppointmentRequest, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute(
        """
        SELECT a.id, c.name AS customer_name, c.phone, s.name AS service_name,
               s.price_cents, a.nail_color, a.datetime, a.status, a.notes
        FROM appointments a
        JOIN customers c ON c.id = a.customer_id
        JOIN services s ON s.id = a.service_id
        WHERE a.id = ?
        """,
        (body.appointment_id,),
    ).fetchone()

    if row is None:
        return {"found": False, "appointment": None}

    return {"found": True, "appointment": _appointment_row_to_dict(row)}


@router.post("/list_available_slots")
def list_available_slots(body: ListAvailableSlotsRequest, db: sqlite3.Connection = Depends(get_db)):
    # Validate date format
    try:
        target_date = datetime.strptime(body.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    # Look up service duration if provided
    duration_minutes = 30  # default slot size
    if body.service_name:
        svc_row = db.execute(
            "SELECT duration_minutes FROM services WHERE LOWER(name) = LOWER(?)",
            (body.service_name,),
        ).fetchone()
        if svc_row:
            duration_minutes = svc_row["duration_minutes"]

    # Generate all 30-min slot start times 09:00–19:00
    all_slots = []
    slot_time = datetime.strptime(f"{body.date} 09:00", "%Y-%m-%d %H:%M")
    end_of_day = datetime.strptime(f"{body.date} 19:00", "%Y-%m-%d %H:%M")
    while slot_time < end_of_day:
        all_slots.append(slot_time)
        slot_time += timedelta(minutes=30)

    # Fetch booked appointments for that date with their service durations
    booked_rows = db.execute(
        """
        SELECT a.datetime, s.duration_minutes
        FROM appointments a
        JOIN services s ON s.id = a.service_id
        WHERE a.datetime LIKE ?
          AND a.status NOT IN ('Cancelled', 'No-Show')
        """,
        (f"{body.date}%",),
    ).fetchall()

    # Build list of (start, end) busy intervals
    busy_intervals = []
    for row in booked_rows:
        try:
            start = datetime.strptime(row["datetime"], "%Y-%m-%d %H:%M")
        except ValueError:
            try:
                start = datetime.strptime(row["datetime"], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        busy_end = start + timedelta(minutes=row["duration_minutes"])
        busy_intervals.append((start, busy_end))

    # Filter slots: a slot is available if [slot, slot+duration) does not overlap any busy interval
    available = []
    for slot in all_slots:
        slot_end = slot + timedelta(minutes=duration_minutes)
        # Slot must not extend past end of day
        if slot_end > end_of_day:
            break
        overlaps = any(
            slot < busy_end and slot_end > busy_start
            for busy_start, busy_end in busy_intervals
        )
        if not overlaps:
            available.append(slot.strftime("%H:%M"))

    return {"date": body.date, "slots": available}


@router.post("/list_today_appointments")
def list_today_appointments(db: sqlite3.Connection = Depends(get_db)):
    today = date.today().isoformat()
    rows = db.execute(
        """
        SELECT a.id, c.name AS customer_name, c.phone, s.name AS service_name,
               s.price_cents, a.nail_color, a.datetime, a.status, a.notes
        FROM appointments a
        JOIN customers c ON c.id = a.customer_id
        JOIN services s ON s.id = a.service_id
        WHERE a.datetime LIKE ?
        ORDER BY a.datetime
        """,
        (f"{today}%",),
    ).fetchall()

    appointments = [_appointment_row_to_dict(r) for r in rows]
    return {"date": today, "count": len(appointments), "appointments": appointments}
