from pydantic import BaseModel
from typing import Optional


class SearchCustomerRequest(BaseModel):
    phone: Optional[str] = None
    name: Optional[str] = None


class GetAppointmentRequest(BaseModel):
    appointment_id: int


class CheckServiceRequest(BaseModel):
    service_name: str


class CheckInventoryRequest(BaseModel):
    color_name: str


class ListAvailableSlotsRequest(BaseModel):
    date: str  # YYYY-MM-DD
    service_name: Optional[str] = None


class BookAppointmentRequest(BaseModel):
    name: str
    phone: str
    service: str
    datetime: str  # ISO 8601
    color: Optional[str] = None
    call_sid: Optional[str] = None


class ModifyAppointmentRequest(BaseModel):
    appointment_id: int
    datetime: Optional[str] = None
    service: Optional[str] = None
    color: Optional[str] = None


class CancelAppointmentRequest(BaseModel):
    appointment_id: int


class RequestCallbackRequest(BaseModel):
    name: str
    phone: str
    reason: str


class HangUpRequest(BaseModel):
    pass


class ListTodayAppointmentsRequest(BaseModel):
    pass


class UpdateAppointmentStatusRequest(BaseModel):
    appointment_id: int
    status: str  # Pending | Confirmed | Completed | Cancelled | No-Show


class ListPendingCallbacksRequest(BaseModel):
    pass


class ResolveCallbackRequest(BaseModel):
    callback_id: int
    status: str  # Called | Resolved


class TriggerReminderCallRequest(BaseModel):
    appointment_id: int


class AppendAppointmentNoteRequest(BaseModel):
    appointment_id: int
    note: str
