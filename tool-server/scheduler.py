import logging
import os
from datetime import datetime, timedelta

import httpx
from apscheduler.schedulers.background import BackgroundScheduler

from database import get_conn

logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID  = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN   = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "")
TWILIO_WEBHOOK_BASE = os.environ.get("TWILIO_WEBHOOK_BASE", "")

_scheduler = BackgroundScheduler()


def _fetch_appointment(appointment_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT
                a.id            AS appointment_id,
                a.service_name,
                a.datetime,
                a.status,
                c.phone         AS customer_phone,
                c.name          AS customer_name
            FROM appointments a
            JOIN customers c ON c.id = a.customer_id
            WHERE a.id = ?
            """,
            (appointment_id,),
        ).fetchone()
    return dict(row) if row else None


def fire_outbound_call(appointment_id: int) -> dict:
    """
    Immediately POST a call trigger to the bridge for the given appointment.
    Returns {"success": True} or {"success": False, "error": "..."}.
    Does NOT check or update reminder_sent — caller decides that.
    """
    row = _fetch_appointment(appointment_id)
    if not row:
        return {"success": False, "error": "Appointment not found"}
    if row["status"] != "scheduled":
        return {"success": False, "error": f"Appointment status is '{row['status']}', not scheduled"}

    payload = {
        "appointment_id": row["appointment_id"],
        "customer_phone": row["customer_phone"],
        "customer_name": row["customer_name"],
        "service_name": row["service_name"],
        "appointment_datetime": row["datetime"],
        "context": (
            f"Reminder call for {row['customer_name']}'s {row['service_name']} "
            f"appointment at {row['datetime']}"
        ),
    }

    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, TWILIO_WEBHOOK_BASE]):
        return {"success": False, "error": "Twilio env vars not configured"}

    reminder_url = f"{TWILIO_WEBHOOK_BASE}/twilio/reminder?appointment_id={appointment_id}"
    try:
        response = httpx.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Calls",
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            data={"To": row["customer_phone"], "From": TWILIO_PHONE_NUMBER, "Url": reminder_url},
            timeout=10,
        )
        response.raise_for_status()
        call_sid = response.json().get("sid")
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO callbacks (appointment_id, triggered_at, twilio_call_sid, status) VALUES (?, ?, ?, 'triggered')",
                (appointment_id, datetime.now().isoformat(), call_sid),
            )
        return {"success": True, "call_sid": call_sid}
    except httpx.HTTPStatusError as exc:
        return {"success": False, "error": f"Twilio returned {exc.response.status_code}: {exc.response.text}"}
    except httpx.RequestError as exc:
        return {"success": False, "error": f"Network error: {exc}"}


def _check_reminders():
    now = datetime.now()
    window_end = now + timedelta(hours=2)

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT a.id AS appointment_id
            FROM appointments a
            WHERE a.status = 'scheduled'
              AND a.reminder_sent = 0
              AND a.datetime BETWEEN ? AND ?
            """,
            (now.isoformat(), window_end.isoformat()),
        ).fetchall()

    for row in rows:
        result = fire_outbound_call(row["appointment_id"])
        if not result["success"]:
            logger.error("Reminder failed for appointment %s: %s", row["appointment_id"], result["error"])
            continue

        with get_conn() as conn:
            conn.execute(
                "UPDATE appointments SET reminder_sent = 1 WHERE id = ?",
                (row["appointment_id"],),
            )


def start_scheduler():
    _scheduler.add_job(_check_reminders, "interval", minutes=5, id="check_reminders")
    _scheduler.start()


def stop_scheduler():
    _scheduler.shutdown()
