from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3

from database import get_db
from tools.customers import upsert_customer

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_appointment_dict(db: sqlite3.Connection, appointment_id: int) -> Optional[dict]:
    row = db.execute(
        """
        SELECT a.id, c.name AS customer_name, c.phone, s.name AS service_name,
               s.price_cents, a.nail_color, a.datetime, a.status, a.notes
        FROM appointments a
        JOIN customers c ON c.id = a.customer_id
        JOIN services s ON s.id = a.service_id
        WHERE a.id = ?
        """,
        (appointment_id,),
    ).fetchone()
    if row is None:
        return None
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


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class BookAppointmentRequest(BaseModel):
    name: str
    phone: str
    service: str
    datetime: str
    color: Optional[str] = None
    call_sid: Optional[str] = None


class ModifyAppointmentRequest(BaseModel):
    appointment_id: int
    datetime: Optional[str] = None
    service: Optional[str] = None
    color: Optional[str] = None


class CancelAppointmentRequest(BaseModel):
    appointment_id: int


class UpdateStatusRequest(BaseModel):
    appointment_id: int
    status: str


class AppendNoteRequest(BaseModel):
    appointment_id: int
    note: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

VALID_STATUSES = {"Pending", "Confirmed", "Completed", "Cancelled", "No-Show"}


@router.post("/book_appointment")
def book_appointment(body: BookAppointmentRequest, db: sqlite3.Connection = Depends(get_db)):
    # Upsert customer
    customer_id = upsert_customer(db, body.name, body.phone)

    # Look up service (case-insensitive)
    svc_row = db.execute(
        "SELECT id, name FROM services WHERE LOWER(name) = LOWER(?)",
        (body.service,),
    ).fetchone()
    if svc_row is None:
        raise HTTPException(status_code=404, detail=f"Service '{body.service}' not found")

    service_id = svc_row["id"]
    service_name = svc_row["name"]

    # Check color availability; book regardless but note if unavailable
    notes = None
    nail_color = body.color
    if body.color:
        color_row = db.execute(
            "SELECT in_stock FROM inventory WHERE LOWER(color_name) LIKE LOWER(?)",
            (f"%{body.color}%",),
        ).fetchone()
        if color_row is None or not color_row["in_stock"]:
            notes = f"Requested color '{body.color}' is not in inventory"

    cursor = db.execute(
        """
        INSERT INTO appointments (customer_id, service_id, nail_color, datetime, status, notes, call_sid)
        VALUES (?, ?, ?, ?, 'Pending', ?, ?)
        """,
        (customer_id, service_id, nail_color, body.datetime, notes, body.call_sid),
    )
    db.commit()
    appointment_id = cursor.lastrowid

    return {
        "success": True,
        "appointment_id": appointment_id,
        "confirmation": f"Booked {service_name} on {body.datetime} for {body.name}",
    }


@router.post("/modify_appointment")
def modify_appointment(body: ModifyAppointmentRequest, db: sqlite3.Connection = Depends(get_db)):
    # Verify appointment exists
    existing = db.execute(
        "SELECT id FROM appointments WHERE id = ?", (body.appointment_id,)
    ).fetchone()
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Appointment {body.appointment_id} not found")

    updates = []
    params = []

    if body.datetime is not None:
        updates.append("datetime = ?")
        params.append(body.datetime)

    if body.service is not None:
        svc_row = db.execute(
            "SELECT id FROM services WHERE LOWER(name) = LOWER(?)",
            (body.service,),
        ).fetchone()
        if svc_row is None:
            raise HTTPException(status_code=404, detail=f"Service '{body.service}' not found")
        updates.append("service_id = ?")
        params.append(svc_row["id"])

    if body.color is not None:
        updates.append("nail_color = ?")
        params.append(body.color)

    if updates:
        params.append(body.appointment_id)
        db.execute(
            f"UPDATE appointments SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        db.commit()

    appt = _fetch_appointment_dict(db, body.appointment_id)
    return {"success": True, "appointment": appt}


@router.post("/cancel_appointment")
def cancel_appointment(body: CancelAppointmentRequest, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute(
        "SELECT id FROM appointments WHERE id = ?", (body.appointment_id,)
    ).fetchone()
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Appointment {body.appointment_id} not found")

    db.execute(
        "UPDATE appointments SET status = 'Cancelled' WHERE id = ?",
        (body.appointment_id,),
    )
    db.commit()
    return {"success": True, "appointment_id": body.appointment_id}


@router.post("/update_appointment_status")
def update_appointment_status(body: UpdateStatusRequest, db: sqlite3.Connection = Depends(get_db)):
    if body.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{body.status}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
        )

    existing = db.execute(
        "SELECT id FROM appointments WHERE id = ?", (body.appointment_id,)
    ).fetchone()
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Appointment {body.appointment_id} not found")

    db.execute(
        "UPDATE appointments SET status = ? WHERE id = ?",
        (body.status, body.appointment_id),
    )
    db.commit()

    appt = _fetch_appointment_dict(db, body.appointment_id)
    return {"success": True, "appointment": appt}


@router.post("/append_appointment_note")
def append_appointment_note(body: AppendNoteRequest, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute(
        "SELECT id, notes FROM appointments WHERE id = ?", (body.appointment_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Appointment {body.appointment_id} not found")

    existing_notes = row["notes"]
    if existing_notes:
        new_notes = f"{existing_notes} | {body.note}"
    else:
        new_notes = body.note

    db.execute(
        "UPDATE appointments SET notes = ? WHERE id = ?",
        (new_notes, body.appointment_id),
    )
    db.commit()
    return {"success": True, "notes": new_notes}
