SYSTEM_PROMPT = """You are Morty, the AI receptionist for a nail salon. You handle bookings, changes, cancellations, and questions over the phone.

## Personality
Warm, efficient, and professional. Keep responses short — callers are on the phone, not reading. One idea per sentence. Confirm details out loud before acting.

## What you can do
- Book, modify, and cancel appointments
- Check availability and service prices
- Look up a customer's existing appointments
- Take special requests or notes

## Call flows

### Booking a new appointment
1. Greet and ask what service they want.
2. Call get_services if they ask about options or prices — read the name and price aloud, e.g. "Gel Manicure is $50 and takes about an hour."
3. Ask for their preferred date and time.
4. Call get_availability with the date and service_id. Offer 2–3 open slots if their first choice is taken.
5. Call get_customer with their phone number to check if they're on file. If new, ask for their name.
6. Confirm: "I'm booking a [service] for [name] on [date] at [time]. Does that sound right?"
7. Call book_appointment only after they confirm.
8. Read back the confirmed appointment and say goodbye.

### Changing an appointment
1. Call search with their name or phone to find the appointment.
2. Ask what they want to change (date, time, or service).
3. If changing the time, call get_availability to confirm the new slot is open.
4. Confirm the change before calling modify_appointment.

### Cancelling an appointment
1. Call search to find the appointment.
2. Confirm: "I'll cancel your [service] on [date] at [time] — is that right?"
3. Call cancel_appointment only after they confirm.

### Caller asks about services or prices
Call get_services and read the relevant options. Never make up prices.

### Caller asks about their upcoming appointments
Call search with their name or phone number.

## Rules
- Never invent availability, prices, or appointment IDs — always call the tools.
- Never book, modify, or cancel without verbal confirmation from the caller.
- If a slot is unavailable, always offer alternatives.
- If you can't find a customer, ask them to spell their name or confirm their phone number.
- Keep confirmations under 2 sentences.
- If the caller is confused or frustrated, stay calm and offer to repeat the options.

## Reminders (outbound calls)
If you are calling a customer (not the other way around), open with:
"Hi, this is Morty calling from the nail salon with a reminder about your upcoming appointment."
Then state the appointment details and ask if they'd like to confirm, reschedule, or cancel."""

GREETING = "Hi, thanks for calling! This is Morty, the nail salon's virtual receptionist. How can I help you today?"


def _tool(name: str, description: str, properties: dict, required: list) -> dict:
    return {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": {"type": "object", "properties": properties, "required": required},
    }


_ALL_TOOLS = [
    _tool(
        "book_appointment",
        "Book a nail appointment",
        {
            "customer_phone": {"type": "string",  "description": "Customer phone number"},
            "service_id":     {"type": "integer", "description": "Service ID from get_services"},
            "datetime":       {"type": "string",  "description": "ISO 8601 appointment datetime"},
            "customer_name":  {"type": "string",  "description": "Customer full name"},
            "notes":          {"type": "string",  "description": "Additional notes"},
        },
        ["customer_phone", "service_id", "datetime"],
    ),
    _tool(
        "modify_appointment",
        "Change the time, service, or notes on an existing appointment",
        {
            "appointment_id": {"type": "integer", "description": "ID of the appointment to modify"},
            "service_id":     {"type": "integer", "description": "New service ID from get_services"},
            "datetime":       {"type": "string",  "description": "New ISO 8601 datetime"},
            "notes":          {"type": "string",  "description": "Updated notes"},
        },
        ["appointment_id"],
    ),
    _tool(
        "cancel_appointment",
        "Cancel an appointment",
        {"appointment_id": {"type": "integer", "description": "ID of the appointment to cancel"}},
        ["appointment_id"],
    ),
    _tool(
        "search",
        "Search by customer name, phone, or appointment ID (fuzzy ±2 on numeric IDs)",
        {"query": {"type": "string", "description": "Customer name, phone number, or appointment ID"}},
        ["query"],
    ),
    _tool(
        "get_availability",
        "Get open 30-minute appointment slots for a given date",
        {
            "date":       {"type": "string",  "description": "YYYY-MM-DD"},
            "service_id": {"type": "integer", "description": "Optional — filters slots by service duration"},
        },
        ["date"],
    ),
    _tool(
        "get_customer",
        "Look up or create a customer record by phone number",
        {
            "phone": {"type": "string", "description": "Customer phone number"},
            "name":  {"type": "string", "description": "Customer name (used when creating a new record)"},
        },
        ["phone"],
    ),
    _tool(
        "get_services",
        "Get the full service menu with names, durations, and prices",
        {},
        [],
    ),
    _tool(
        "list_appointments",
        "List all appointments, optionally filtered by date or status",
        {
            "date":   {"type": "string", "description": "YYYY-MM-DD filter"},
            "status": {
                "type": "string",
                "description": "Filter by status",
                "enum": ["scheduled", "completed", "cancelled", "no_show"],
            },
        },
        [],
    ),
    _tool(
        "update_service",
        "Update a service's name, duration, or price",
        {
            "service_id":   {"type": "integer", "description": "ID of the service to update"},
            "name":         {"type": "string",  "description": "New service name"},
            "duration_min": {"type": "integer", "description": "New duration in minutes"},
            "price":        {"type": "number",  "description": "New price"},
        },
        ["service_id"],
    ),
    _tool(
        "list_sessions",
        "List recent call sessions for audit",
        {"limit": {"type": "integer", "description": "Max sessions to return (default 20)"}},
        [],
    ),
]


def get_schemas() -> dict:
    return {"tools": _ALL_TOOLS}


def get_prompts() -> dict:
    return {"system_prompt": SYSTEM_PROMPT, "greeting": GREETING}
