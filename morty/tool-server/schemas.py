"""
schemas.py — AssemblyAI tool-schema and prompt endpoints for Morty's Nail Salon.

Endpoints:
  GET /tools/schemas?role=consumer|owner  → list of AssemblyAI flat tool definitions
  GET /tools/prompts?role=consumer|owner  → {"system_prompt": ..., "greeting": ...}

The bridge calls /tools/prompts to populate session.update when a call connects,
and /tools/schemas to know which tools to register with the AssemblyAI agent session.
"""

from fastapi import APIRouter

from prompts import CONSUMER_GREETING, CONSUMER_SYSTEM

router = APIRouter()

# ---------------------------------------------------------------------------
# Tool definitions — AssemblyAI flat format
# ---------------------------------------------------------------------------
#
# {
#   "type": "function",
#   "name": "tool_name",
#   "description": "...",
#   "parameters": {
#     "type": "object",
#     "properties": { ... },
#     "required": [...]
#   }
# }

_CONSUMER_TOOLS: list[dict] = [
    {
        "type": "function",
        "name": "search_customer",
        "description": (
            "Look up an existing customer by phone number and/or name. "
            "Call this immediately at the start of every inbound call using the caller's phone number "
            "so you can greet them by name and see whether they have upcoming appointments."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "phone": {
                    "type": "string",
                    "description": (
                        "Customer phone number in E.164 format (e.g. +12125551234). "
                        "Optional when name is provided."
                    ),
                },
                "name": {
                    "type": "string",
                    "description": (
                        "Full or partial customer name to search by. "
                        "Optional when phone is provided."
                    ),
                },
            },
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "get_appointment",
        "description": (
            "Fetch full details for a single appointment by its ID — service, date/time, "
            "nail color, status, and notes. Use this when a customer references a specific "
            "appointment, or before modifying or cancelling one."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {
                    "type": "integer",
                    "description": "The numeric ID of the appointment to retrieve.",
                },
            },
            "required": ["appointment_id"],
        },
    },
    {
        "type": "function",
        "name": "list_services",
        "description": (
            "Return the full menu of nail services offered by Morty's Nail Salon, including name, "
            "category, price, and duration. Call this when a customer asks what services are "
            "available or wants to browse the menu."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "check_service",
        "description": (
            "Look up a specific service by name to get its price, duration, category, and "
            "description. Call this when a customer asks about pricing or details for a "
            "particular service."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": (
                        "Exact or approximate service name (e.g. 'Gel Manicure', 'Spa Pedicure')."
                    ),
                },
            },
            "required": ["service_name"],
        },
    },
    {
        "type": "function",
        "name": "check_inventory",
        "description": (
            "Check whether a specific nail color is in stock. Returns in-stock status and up to "
            "3 alternative in-stock colors if the requested color is unavailable. Always call "
            "this before booking when a customer specifies a color, and offer alternatives if "
            "the color is out of stock."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "color_name": {
                    "type": "string",
                    "description": (
                        "The nail color the customer is requesting "
                        "(e.g. 'Ballet Slipper Pink', 'Midnight Black')."
                    ),
                },
            },
            "required": ["color_name"],
        },
    },
    {
        "type": "function",
        "name": "list_available_slots",
        "description": (
            "Return open appointment time slots for a given date. Optionally filter by service "
            "to account for the correct duration block. Always call this before offering times "
            "to a customer so you never promise a slot that isn't open."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "The date to check in YYYY-MM-DD format (e.g. '2025-06-15').",
                },
                "service_name": {
                    "type": "string",
                    "description": (
                        "Optional service name — filters slots to those long enough for the "
                        "service's duration."
                    ),
                },
            },
            "required": ["date"],
        },
    },
    {
        "type": "function",
        "name": "book_appointment",
        "description": (
            "Create a new appointment for a customer. Call this only after confirming the "
            "customer's name, phone, desired service, date/time, and (if requested) nail color. "
            "After a successful booking, read back the appointment ID, service, datetime, and "
            "color to the customer."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Customer's full name.",
                },
                "phone": {
                    "type": "string",
                    "description": "Customer's phone number.",
                },
                "service": {
                    "type": "string",
                    "description": "Exact name of the service to book (e.g. 'Gel Manicure').",
                },
                "datetime": {
                    "type": "string",
                    "description": (
                        "Appointment date and time in ISO 8601 format "
                        "(e.g. '2025-06-15T14:00:00')."
                    ),
                },
                "color": {
                    "type": "string",
                    "description": (
                        "Optional nail color the customer selected — must be confirmed in "
                        "stock via check_inventory first."
                    ),
                },
            },
            "required": ["name", "phone", "service", "datetime"],
        },
    },
    {
        "type": "function",
        "name": "modify_appointment",
        "description": (
            "Update one or more fields of an existing appointment: date/time, service, or nail "
            "color. Provide only the fields that are changing. Call get_appointment first if you "
            "need to confirm the current details before making a change."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {
                    "type": "integer",
                    "description": "The ID of the appointment to update.",
                },
                "datetime": {
                    "type": "string",
                    "description": "New date and time in ISO 8601 format. Omit if not changing.",
                },
                "service": {
                    "type": "string",
                    "description": "New service name. Omit if not changing.",
                },
                "color": {
                    "type": "string",
                    "description": "New nail color. Omit if not changing.",
                },
            },
            "required": ["appointment_id"],
        },
    },
    {
        "type": "function",
        "name": "cancel_appointment",
        "description": (
            "Cancel an existing appointment by ID. Confirm the appointment details with the "
            "customer before calling this. After success, verbally confirm the cancellation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {
                    "type": "integer",
                    "description": "The ID of the appointment to cancel.",
                },
            },
            "required": ["appointment_id"],
        },
    },
    {
        "type": "function",
        "name": "request_callback",
        "description": (
            "Log a callback request when a customer needs follow-up that can't be handled right "
            "now — e.g. special requests, pricing questions, or complaints. The salon will return "
            "their call."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Customer's full name.",
                },
                "phone": {
                    "type": "string",
                    "description": "Best phone number to call them back on.",
                },
                "reason": {
                    "type": "string",
                    "description": "Brief description of why they need a callback.",
                },
            },
            "required": ["name", "phone", "reason"],
        },
    },
    {
        "type": "function",
        "name": "hang_up",
        "description": (
            "End the call cleanly. Call this after a natural sign-off — when the customer has "
            "no more questions, after completing a booking or cancellation, or if the caller is "
            "unresponsive. Always say a brief goodbye before invoking hang_up."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]

_OWNER_EXTRA_TOOLS: list[dict] = [
    {
        "type": "function",
        "name": "list_today_appointments",
        "description": (
            "Return all appointments scheduled for today, including customer name, service, "
            "time, status, and nail color. Use this when the owner wants an overview of the "
            "day's schedule."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "update_appointment_status",
        "description": (
            "Change the status of an appointment. Valid statuses: Pending, Confirmed, Completed, "
            "Cancelled, No-Show. Use this to confirm arrivals, mark services as done, or flag "
            "no-shows."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {
                    "type": "integer",
                    "description": "The ID of the appointment to update.",
                },
                "status": {
                    "type": "string",
                    "enum": ["Pending", "Confirmed", "Completed", "Cancelled", "No-Show"],
                    "description": "The new status to set on the appointment.",
                },
            },
            "required": ["appointment_id", "status"],
        },
    },
    {
        "type": "function",
        "name": "list_pending_callbacks",
        "description": (
            "Return all unresolved callback requests from customers. Use this when the owner "
            "wants to review who still needs to be called back."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "resolve_callback",
        "description": (
            "Mark a callback request as Called or Resolved after the owner has followed up "
            "with the customer."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "callback_id": {
                    "type": "integer",
                    "description": "The ID of the callback record to update.",
                },
                "status": {
                    "type": "string",
                    "enum": ["Called", "Resolved"],
                    "description": (
                        "'Called' if contact was attempted; 'Resolved' if the matter is fully "
                        "handled."
                    ),
                },
            },
            "required": ["callback_id", "status"],
        },
    },
    {
        "type": "function",
        "name": "trigger_reminder_call",
        "description": (
            "Immediately place an outbound reminder call to a customer for a specific "
            "appointment, outside of the normal 15-minute automated schedule. Use this when "
            "the owner wants to manually send a reminder right now."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {
                    "type": "integer",
                    "description": "The ID of the appointment to send a reminder call for.",
                },
            },
            "required": ["appointment_id"],
        },
    },
    {
        "type": "function",
        "name": "append_appointment_note",
        "description": (
            "Append a timestamped note to an existing appointment. Notes are never overwritten. "
            "Use this to record special instructions, preferences, or follow-up items the "
            "owner mentions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {
                    "type": "integer",
                    "description": "The ID of the appointment to add a note to.",
                },
                "note": {
                    "type": "string",
                    "description": (
                        "The note text to append "
                        "(e.g. 'Customer prefers extra hydration treatment')."
                    ),
                },
            },
            "required": ["appointment_id", "note"],
        },
    },
]

# All callers get the full tool set — no role distinction
ALL_TOOLS: list[dict] = _CONSUMER_TOOLS + _OWNER_EXTRA_TOOLS

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/tools/schemas")
def get_schemas():
    """Return AssemblyAI-format tool definitions. Bridge calls this on startup."""
    return {"tools": ALL_TOOLS}


@router.get("/tools/prompts")
def get_prompts():
    """Return system_prompt and greeting. Bridge calls this to populate session.update."""
    return {"system_prompt": CONSUMER_SYSTEM, "greeting": CONSUMER_GREETING}
