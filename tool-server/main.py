import os
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query, Body
from dotenv import load_dotenv

from database import init_db, get_conn
from models import (
    BookAppointmentRequest,
    ModifyAppointmentRequest,
    CancelAppointmentRequest,
    SessionStartRequest,
    SessionEndRequest,
)
from scheduler import start_scheduler, stop_scheduler, fire_outbound_call
from sessions import start_session, end_session, list_sessions
from tool_schemas import get_schemas, get_prompts
from tools.crud import (
    book_appointment,
    modify_appointment,
    cancel_appointment,
    list_appointments,
    update_service,
)
from tools.search import search
from tools.customers import get_or_create_customer, get_availability, get_services

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Morty Tool Server", lifespan=lifespan)


# ── tool dispatch (catch-all) ─────────────────────────────────────────────────

def _resolve_service(body: dict) -> dict:
    """Translate service_id → service_name in body before passing to crud functions."""
    sid = body.get("service_id")
    if sid is not None and "service_name" not in body:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT name FROM services WHERE id = ?", (sid,)
            ).fetchone()
        if row:
            body = {**body, "service_name": row["name"]}
    return body


@app.post("/tools/{tool_name}")
def route_tool(tool_name: str, body: dict[str, Any] = Body(default={})):
    body = _resolve_service(body)
    try:
        match tool_name:
            case "book_appointment":
                return book_appointment(BookAppointmentRequest(**body))
            case "modify_appointment":
                return modify_appointment(ModifyAppointmentRequest(**body))
            case "cancel_appointment":
                return cancel_appointment(CancelAppointmentRequest(**body))
            case "search":
                return search(body.get("query", ""))
            case "get_availability":
                return {"slots": get_availability(body["date"], body.get("service_name"))}
            case "get_customer":
                return get_or_create_customer(body["phone"], body.get("name"))
            case "get_services":
                return get_services()
            case "list_appointments":
                return list_appointments(body.get("date"), body.get("status"))
            case "update_service":
                return update_service(
                    body["service_id"],
                    body.get("name"),
                    body.get("duration_min"),
                    body.get("price"),
                )
            case "list_sessions":
                return list_sessions(body.get("limit", 20))
            case _:
                raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_name}")
    except KeyError as e:
        raise HTTPException(status_code=422, detail=f"Missing required parameter: {e}")


# ── schema + prompt config ────────────────────────────────────────────────────

@app.get("/tools/schemas")
def route_schemas():
    return get_schemas()


@app.get("/tools/prompts")
def route_prompts():
    return get_prompts()


# ── session audit ─────────────────────────────────────────────────────────────

@app.post("/sessions/start")
def route_session_start(req: SessionStartRequest):
    return start_session(req.session_id, req.phone, req.role, req.started_at)


@app.post("/sessions/end")
def route_session_end(req: SessionEndRequest):
    return end_session(req.session_id, req.ended_at, req.duration_sec)


# ── outbound (manual trigger) ─────────────────────────────────────────────────

@app.post("/outbound/trigger")
def route_outbound_trigger(appointment_id: int = Query(...)):
    return fire_outbound_call(appointment_id)


# ── health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
