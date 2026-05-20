import os
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from database import init_db, get_conn
from models import SessionStartRequest, SessionEndRequest
from scheduler import start_scheduler, stop_scheduler, fire_outbound_call
from sessions import start_session, end_session, list_sessions
from tool_schemas import get_schemas, get_prompts

# Dashboard functions
from routes.dashboard import (
    get_today_appointments,
    get_appointment_by_id,
    search_dashboard,
    get_availability_slots,
    book,
    modify,
    cancel,
    get_customer_by_phone,
    update_customer,
    get_services_list,
    create_service,
    update_service_rest,
    delete_service,
    get_analytics,
)

# Voice-agent tool functions
from tools.crud import (
    book_appointment, modify_appointment, cancel_appointment,
    list_appointments, update_service,
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD REST API  (called by the Next.js front-end)
# ═══════════════════════════════════════════════════════════════════════════════

# ── appointments ──────────────────────────────────────────────────────────────

@app.get("/tools/appointments/today")
def route_today():
    return get_today_appointments()


@app.get("/tools/appointments/{appointment_id}")
def route_appointment(appointment_id: int):
    result = get_appointment_by_id(appointment_id)
    if not result:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return result


@app.get("/tools/search")
def route_search_get(q: str = Query(...)):
    return search_dashboard(q)


@app.get("/tools/availability")
def route_availability_get(
    date: str = Query(...),
    service_id: Optional[int] = Query(None),
):
    return get_availability_slots(date, service_id)


# Dashboard book/modify/cancel — different payload shapes from voice-agent tools

class BookPayload(BaseModel):
    customer_phone: str
    service: str
    datetime: str
    customer_name: Optional[str] = None
    duration_min: Optional[int] = None

class ModifyPayload(BaseModel):
    appointment_id: int
    changes: dict = {}

class CancelPayload(BaseModel):
    appointment_id: int

@app.post("/tools/book")
def route_book(payload: BookPayload):
    return book(payload.customer_phone, payload.service, payload.datetime,
                payload.customer_name, payload.duration_min)

@app.post("/tools/modify")
def route_modify(payload: ModifyPayload):
    return modify(payload.appointment_id, payload.changes)

@app.post("/tools/cancel")
def route_cancel(payload: CancelPayload):
    return cancel(payload.appointment_id)


# ── customers ─────────────────────────────────────────────────────────────────

@app.get("/tools/customer")
def route_customer_get(
    phone: str = Query(...),
    name: Optional[str] = Query(None),
):
    return get_customer_by_phone(phone, name)


class CustomerUpdatePayload(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None

@app.patch("/tools/customer/{customer_id}")
def route_customer_update(customer_id: int, payload: CustomerUpdatePayload):
    result = update_customer(customer_id, payload.name, payload.notes)
    if not result:
        raise HTTPException(status_code=404, detail="Customer not found")
    return result


# ── services ──────────────────────────────────────────────────────────────────

@app.get("/tools/services")
def route_services_list():
    return get_services_list()


class ServiceCreatePayload(BaseModel):
    name: str
    duration_min: int
    price: float

class ServiceUpdatePayload(BaseModel):
    name: Optional[str] = None
    duration_min: Optional[int] = None
    price: Optional[float] = None
    active: Optional[bool] = None

@app.post("/tools/services")
def route_services_create(payload: ServiceCreatePayload):
    return create_service(payload.name, payload.duration_min, payload.price)

@app.patch("/tools/services/{service_id}")
def route_services_update(service_id: int, payload: ServiceUpdatePayload):
    result = update_service_rest(service_id, payload.name, payload.duration_min,
                                 payload.price, payload.active)
    if not result:
        raise HTTPException(status_code=404, detail="Service not found")
    return result

@app.delete("/tools/services/{service_id}")
def route_services_delete(service_id: int):
    return delete_service(service_id)


# ── reminders ─────────────────────────────────────────────────────────────────

@app.post("/tools/remind/{appointment_id}")
def route_remind(appointment_id: int):
    result = fire_outbound_call(appointment_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return {
        "appointment_id": appointment_id,
        "status": "sent",
        "message": f"Reminder call initiated. Call SID: {result.get('call_sid', 'n/a')}",
    }


# ── analytics ─────────────────────────────────────────────────────────────────

@app.get("/tools/analytics")
def route_analytics(days: int = Query(default=30)):
    return get_analytics(days)


# ═══════════════════════════════════════════════════════════════════════════════
# VOICE-AGENT TOOL DISPATCH  (called by the AssemblyAI bridge)
# ═══════════════════════════════════════════════════════════════════════════════

def _resolve_service(body: dict) -> dict:
    sid = body.get("service_id")
    if sid is not None and "service_name" not in body:
        with get_conn() as conn:
            row = conn.execute("SELECT name FROM services WHERE id=?", (sid,)).fetchone()
        if row:
            body = {**body, "service_name": row["name"]}
    return body


from models import BookAppointmentRequest, ModifyAppointmentRequest, CancelAppointmentRequest

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
                return update_service(body["service_id"], body.get("name"),
                                      body.get("duration_min"), body.get("price"))
            case "list_sessions":
                return list_sessions(body.get("limit", 20))
            case _:
                raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_name}")
    except KeyError as e:
        raise HTTPException(status_code=422, detail=f"Missing required parameter: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG + SESSION AUDIT
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/tools/schemas")
def route_schemas():
    return get_schemas()

@app.get("/tools/prompts")
def route_prompts():
    return get_prompts()

@app.post("/sessions/start")
def route_session_start(req: SessionStartRequest):
    return start_session(req.session_id, req.phone, req.role, req.started_at)

@app.post("/sessions/end")
def route_session_end(req: SessionEndRequest):
    return end_session(req.session_id, req.ended_at, req.duration_sec)

@app.post("/outbound/trigger")
def route_outbound_trigger(appointment_id: int = Query(...)):
    return fire_outbound_call(appointment_id)

@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
