from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sqlite3

from database import get_db
from tools.customers import upsert_customer

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RequestCallbackRequest(BaseModel):
    name: str
    phone: str
    reason: str


class ResolveCallbackRequest(BaseModel):
    callback_id: int


class TriggerReminderCallRequest(BaseModel):
    appointment_id: int
    status: str  # 'Called' or 'Resolved'


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/request_callback")
def request_callback(body: RequestCallbackRequest, db: sqlite3.Connection = Depends(get_db)):
    from tools.customers import normalize_phone

    normalized_phone = normalize_phone(body.phone)
    customer_id = upsert_customer(db, body.name, body.phone)

    cursor = db.execute(
        "INSERT INTO callbacks (customer_id, phone, reason, status) VALUES (?, ?, ?, 'Pending')",
        (customer_id, normalized_phone, body.reason),
    )
    db.commit()
    return {"success": True, "callback_id": cursor.lastrowid}


@router.post("/list_pending_callbacks")
def list_pending_callbacks(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute(
        """
        SELECT cb.id, cb.phone, cb.reason, cb.status, cb.attempts,
               cb.created_at, cb.resolved_at,
               c.name AS customer_name
        FROM callbacks cb
        LEFT JOIN customers c ON c.id = cb.customer_id
        WHERE cb.status = 'Pending'
        ORDER BY cb.created_at
        """,
    ).fetchall()

    callbacks = [
        {
            "id": r["id"],
            "customer_name": r["customer_name"],
            "phone": r["phone"],
            "reason": r["reason"],
            "status": r["status"],
            "attempts": r["attempts"],
            "created_at": r["created_at"],
            "resolved_at": r["resolved_at"],
        }
        for r in rows
    ]
    return {"count": len(callbacks), "callbacks": callbacks}


@router.post("/resolve_callback")
def resolve_callback(body: ResolveCallbackRequest, db: sqlite3.Connection = Depends(get_db)):
    if body.status not in ("Called", "Resolved"):
        raise HTTPException(
            status_code=400,
            detail="status must be 'Called' or 'Resolved'",
        )

    existing = db.execute(
        "SELECT id FROM callbacks WHERE id = ?", (body.callback_id,)
    ).fetchone()
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Callback {body.callback_id} not found")

    if body.status == "Resolved":
        db.execute(
            "UPDATE callbacks SET status = ?, resolved_at = datetime('now') WHERE id = ?",
            (body.status, body.callback_id),
        )
    else:
        db.execute(
            "UPDATE callbacks SET status = ? WHERE id = ?",
            (body.status, body.callback_id),
        )
    db.commit()
    return {"success": True}


@router.post("/trigger_reminder_call")
def trigger_reminder_call(body: TriggerReminderCallRequest):
    from scheduler import trigger_reminder_call_for
    return trigger_reminder_call_for(body.appointment_id)


@router.post("/hang_up")
def hang_up():
    """Signal to the bridge that the call should be ended. Actual hangup is handled externally."""
    return {"success": True}
