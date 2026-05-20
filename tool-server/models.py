from pydantic import BaseModel, field_validator
from typing import Optional


class BookAppointmentRequest(BaseModel):
    customer_phone: str
    customer_name: Optional[str] = None
    service_name: Optional[str] = None
    datetime: str  # ISO 8601, e.g. "2026-05-20T14:00:00"
    notes: Optional[str] = None


class ModifyAppointmentRequest(BaseModel):
    appointment_id: int
    service_name: Optional[str] = None
    datetime: Optional[str] = None
    notes: Optional[str] = None


class CancelAppointmentRequest(BaseModel):
    appointment_id: int


class SearchRequest(BaseModel):
    query: str  # name, phone fragment, or numeric appointment ID


class GetCustomerRequest(BaseModel):
    phone: str
    name: Optional[str] = None  # if provided, upserts name on lookup


class GetAvailabilityRequest(BaseModel):
    date: str          # "YYYY-MM-DD"
    service_name: Optional[str] = None


# ── session tracking ──────────────────────────────────────────────────────────

class SessionStartRequest(BaseModel):
    session_id: str
    phone: str
    role: str
    started_at: str  # ISO 8601


class SessionEndRequest(BaseModel):
    session_id: str
    ended_at: str    # ISO 8601
    duration_sec: Optional[int] = None


# ── outbound trigger (tool-server → bridge) ───────────────────────────────────

class OutboundTrigger(BaseModel):
    appointment_id: int
    customer_phone: str
    customer_name: str
    service_name: str
    appointment_datetime: str
    context: str  # pre-built system prompt snippet for the bridge
