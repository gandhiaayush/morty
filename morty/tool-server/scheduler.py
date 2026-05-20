"""
scheduler.py — APScheduler background jobs for Luxe Nails tool-server.

Exports:
  start_scheduler()              — register jobs and start the scheduler
  stop_scheduler()               — graceful shutdown
  trigger_reminder_call_for(id)  — callable directly from the /tools endpoint
"""

import base64
import logging
import os

import httpx
from apscheduler.schedulers.background import BackgroundScheduler

from database import _open_db as get_db

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _trigger_twilio_call(phone: str, name: str, appointment_id: int) -> dict:
    """
    Fire a Twilio outbound call for a reminder.  Never raises — callers log the
    returned dict and move on regardless of success/failure.
    """
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    from_number = os.environ.get("TWILIO_PHONE_NUMBER", "")
    webhook_base = os.environ.get("TWILIO_WEBHOOK_BASE", "").rstrip("/")

    if not all([sid, token, from_number, webhook_base]):
        msg = "Twilio env vars not fully configured (SID, TOKEN, PHONE, WEBHOOK_BASE required)"
        logger.error("[scheduler] %s", msg)
        return {"success": False, "call_sid": None, "error": msg}

    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json"
    credentials = base64.b64encode(f"{sid}:{token}".encode()).decode()
    webhook_url = (
        f"{webhook_base}/voice"
        f"?outbound=true"
        f"&appointmentId={appointment_id}"
        f"&customerName={httpx.URL(name).path}"  # percent-encode name via httpx
    )
    # httpx.URL encoding isn't right for a query value — do it properly:
    from urllib.parse import quote
    webhook_url = (
        f"{webhook_base}/voice"
        f"?outbound=true"
        f"&appointmentId={appointment_id}"
        f"&customerName={quote(name, safe='')}"
    )

    try:
        resp = httpx.post(
            url,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "To": phone,
                "From": from_number,
                "Url": webhook_url,
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        call_sid = resp.json().get("sid")
        logger.info(
            "[scheduler] Reminder call placed → appointment=%s phone=%s call_sid=%s",
            appointment_id, phone, call_sid,
        )
        return {"success": True, "call_sid": call_sid, "error": None}
    except httpx.HTTPStatusError as exc:
        msg = f"Twilio HTTP error {exc.response.status_code}: {exc.response.text[:200]}"
        logger.error("[scheduler] %s (appointment=%s)", msg, appointment_id)
        return {"success": False, "call_sid": None, "error": msg}
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        logger.error("[scheduler] Unexpected error placing call (appointment=%s): %s", appointment_id, msg)
        return {"success": False, "call_sid": None, "error": msg}


def _run_reminder_job() -> None:
    """
    Scheduled task — runs every 15 minutes.
    Finds appointments that:
      - status IN ('Pending', 'Confirmed')
      - reminder_sent_at IS NULL
      - datetime is between 23 h and 25 h from now
    Places a Twilio call for each and marks reminder_sent_at.
    """
    logger.info("[scheduler] Running reminder job...")
    db = get_db()
    try:
        rows = db.execute(
            """
            SELECT
                a.id            AS appointment_id,
                a.datetime      AS appt_datetime,
                c.name          AS customer_name,
                c.phone         AS customer_phone
            FROM appointments a
            JOIN customers c ON c.id = a.customer_id
            WHERE a.status IN ('Pending', 'Confirmed')
              AND a.reminder_sent_at IS NULL
              AND datetime(a.datetime) BETWEEN datetime('now', '+23 hours')
                                           AND datetime('now', '+25 hours')
            """
        ).fetchall()

        logger.info("[scheduler] %d appointment(s) eligible for reminders.", len(rows))

        for row in rows:
            appt_id = row["appointment_id"]
            phone = row["customer_phone"]
            name = row["customer_name"]

            logger.info(
                "[scheduler] Triggering reminder call → appointment=%s customer=%s phone=%s",
                appt_id, name, phone,
            )

            result = _trigger_twilio_call(phone, name, appt_id)

            # Mark reminder_sent_at regardless of call outcome so we don't spam
            db.execute(
                "UPDATE appointments SET reminder_sent_at = datetime('now') WHERE id = ?",
                (appt_id,),
            )
            db.commit()

            if result["success"]:
                logger.info(
                    "[scheduler] Reminder sent → appointment=%s call_sid=%s",
                    appt_id, result["call_sid"],
                )
            else:
                logger.warning(
                    "[scheduler] Reminder call failed → appointment=%s error=%s",
                    appt_id, result["error"],
                )
    except Exception as exc:  # noqa: BLE001
        logger.exception("[scheduler] Reminder job crashed: %s", exc)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_scheduler() -> None:
    """Create and start the APScheduler BackgroundScheduler, registering all jobs."""
    global _scheduler
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        _run_reminder_job,
        trigger="interval",
        minutes=15,
        id="reminder_job",
        name="Appointment Reminder Caller",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("[scheduler] Started — reminder job runs every 15 minutes.")


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[scheduler] Stopped.")


def get_scheduler() -> BackgroundScheduler | None:
    return _scheduler


def trigger_reminder_call_for(appointment_id: int) -> dict:
    """
    Immediately trigger a reminder call for a specific appointment.
    Used by the POST /tools/trigger_reminder_call endpoint.

    Returns:
        {"success": bool, "call_sid": str | None, "error": str | None}
    """
    db = get_db()
    try:
        row = db.execute(
            """
            SELECT
                a.id       AS appointment_id,
                c.name     AS customer_name,
                c.phone    AS customer_phone
            FROM appointments a
            JOIN customers c ON c.id = a.customer_id
            WHERE a.id = ?
            """,
            (appointment_id,),
        ).fetchone()

        if row is None:
            return {
                "success": False,
                "call_sid": None,
                "error": f"Appointment {appointment_id} not found",
            }

        result = _trigger_twilio_call(
            phone=row["customer_phone"],
            name=row["customer_name"],
            appointment_id=appointment_id,
        )

        if result["success"]:
            # Record that we sent a reminder
            db.execute(
                "UPDATE appointments SET reminder_sent_at = datetime('now') WHERE id = ? AND reminder_sent_at IS NULL",
                (appointment_id,),
            )
            db.commit()

        return result
    finally:
        db.close()
