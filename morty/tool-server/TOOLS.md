# Morty Tool-Server — Tool Reference

All tools are invoked via `POST /tools/{tool_name}` with a JSON body. All responses are JSON. HTTP 200 = success. HTTP 4xx/5xx = error with `{ "error": "<message>" }`.

---

## Consumer Tools

These tools are available in all sessions (consumer and owner).

---

### `search_customer`

**Description:** Look up a customer record by phone number or name. Use this at the start of any call to personalize the interaction and retrieve the customer's ID for subsequent tool calls. If no match is found, the customer is a new caller.

**Request parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `phone` | string | Optional | Caller's phone in E.164 format, e.g. `+15551234567` |
| `name` | string | Optional | Full or partial customer name (case-insensitive) |

At least one of `phone` or `name` must be provided.

**Response shape:**

| Field | Type | Description |
|-------|------|-------------|
| `found` | boolean | Whether a matching customer was found |
| `customer` | object \| null | Customer record if found, otherwise null |
| `customer.id` | integer | Internal customer ID |
| `customer.name` | string | Full name |
| `customer.phone` | string | E.164 phone number |
| `customer.email` | string \| null | Email address |
| `customer.notes` | string \| null | Staff notes about this customer |
| `customer.created_at` | string | ISO 8601 timestamp of first visit |

**Example request:**

```json
{ "phone": "+15551234567" }
```

**Example response:**

```json
{
  "found": true,
  "customer": {
    "id": 7,
    "name": "Maria Garcia",
    "phone": "+15551234567",
    "email": "maria@example.com",
    "notes": "Prefers OPI brand. Allergic to acetone.",
    "created_at": "2025-11-03T10:30:00"
  }
}
```

---

### `get_appointment`

**Description:** Retrieve details of an existing appointment. Use when a caller asks about their upcoming or past appointment. Can look up by appointment ID or by customer phone.

**Request parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `appointment_id` | integer | Optional | Specific appointment ID |
| `customer_phone` | string | Optional | Retrieve the next upcoming appointment for this phone number |

**Response shape:**

| Field | Type | Description |
|-------|------|-------------|
| `found` | boolean | Whether an appointment was found |
| `appointment` | object \| null | Appointment record or null |
| `appointment.id` | integer | Appointment ID |
| `appointment.customer_name` | string | Customer's name |
| `appointment.customer_phone` | string | Customer's phone |
| `appointment.service_name` | string | Name of the booked service |
| `appointment.datetime` | string | ISO 8601 datetime |
| `appointment.duration_min` | integer | Service duration in minutes |
| `appointment.technician` | string | Assigned technician or "Any" |
| `appointment.status` | string | `confirmed`, `completed`, `cancelled`, `no_show` |
| `appointment.notes` | string \| null | Staff notes |

**Example request:**

```json
{ "customer_phone": "+15551234567" }
```

**Example response:**

```json
{
  "found": true,
  "appointment": {
    "id": 42,
    "customer_name": "Maria Garcia",
    "customer_phone": "+15551234567",
    "service_name": "Gel Manicure",
    "datetime": "2026-05-21T14:00:00",
    "duration_min": 45,
    "technician": "Lisa",
    "status": "confirmed",
    "notes": null
  }
}
```

---

### `list_services`

**Description:** Return the full menu of available services with prices and durations. Call this when a customer asks what services are offered, requests pricing, or needs to choose a service to book.

**Request parameters:** None required.

**Response shape:**

| Field | Type | Description |
|-------|------|-------------|
| `services` | array | List of service objects |
| `services[].id` | integer | Service ID (needed for booking) |
| `services[].name` | string | Service name |
| `services[].price` | number | Price in USD |
| `services[].duration_min` | integer | Duration in minutes |
| `services[].description` | string | Short description |
| `services[].available` | boolean | Whether currently offered |

**Example request:**

```json
{}
```

**Example response:**

```json
{
  "services": [
    { "id": 1, "name": "Classic Manicure", "price": 25.00, "duration_min": 30, "description": "Nail shaping, cuticle care, and regular polish", "available": true },
    { "id": 2, "name": "Gel Manicure", "price": 45.00, "duration_min": 45, "description": "Long-lasting gel polish with UV cure", "available": true },
    { "id": 3, "name": "Classic Pedicure", "price": 35.00, "duration_min": 45, "description": "Foot soak, nail shaping, and regular polish", "available": true },
    { "id": 4, "name": "Gel Pedicure", "price": 55.00, "duration_min": 60, "description": "Pedicure with long-lasting gel polish", "available": true },
    { "id": 5, "name": "Acrylic Full Set", "price": 65.00, "duration_min": 90, "description": "Full set of acrylic nail extensions", "available": true },
    { "id": 6, "name": "Acrylic Fill", "price": 35.00, "duration_min": 60, "description": "Two-week acrylic maintenance fill", "available": true },
    { "id": 7, "name": "Nail Art (per nail)", "price": 5.00, "duration_min": 5, "description": "Custom nail art design per nail", "available": true },
    { "id": 8, "name": "Polish Change", "price": 15.00, "duration_min": 20, "description": "Remove old polish and apply new color", "available": true }
  ]
}
```

---

### `check_service`

**Description:** Get detailed information about a single service by name or ID. Use when a customer wants specifics about one service — price, duration, what it includes.

**Request parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `service_id` | integer | Optional | Service ID |
| `service_name` | string | Optional | Service name (partial match supported) |

**Response shape:**

| Field | Type | Description |
|-------|------|-------------|
| `found` | boolean | Whether the service was found |
| `service` | object \| null | Service details or null |
| `service.id` | integer | Service ID |
| `service.name` | string | Service name |
| `service.price` | number | Price in USD |
| `service.duration_min` | integer | Duration in minutes |
| `service.description` | string | Full description |
| `service.available` | boolean | Whether currently offered |

**Example request:**

```json
{ "service_name": "gel manicure" }
```

**Example response:**

```json
{
  "found": true,
  "service": {
    "id": 2,
    "name": "Gel Manicure",
    "price": 45.00,
    "duration_min": 45,
    "description": "Long-lasting gel polish with UV cure. Lasts 2–3 weeks without chipping.",
    "available": true
  }
}
```

---

### `check_inventory`

**Description:** Check available nail polish colors or other inventory items. Use when a customer asks what colors are in stock or whether a specific color/brand is available.

**Request parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `color_name` | string | Optional | Search by color name or shade (partial match) |
| `brand` | string | Optional | Filter by brand (e.g. OPI, Essie, CND) |
| `type` | string | Optional | Filter by type: `regular`, `gel`, `acrylic`, `dip` |

**Response shape:**

| Field | Type | Description |
|-------|------|-------------|
| `items` | array | Matching inventory items |
| `items[].id` | integer | Inventory item ID |
| `items[].name` | string | Color/product name |
| `items[].brand` | string | Brand name |
| `items[].type` | string | Product type |
| `items[].shade` | string | Color description |
| `items[].in_stock` | boolean | Whether currently available |
| `total_found` | integer | Total number of matching items |

**Example request:**

```json
{ "brand": "OPI", "type": "gel" }
```

**Example response:**

```json
{
  "items": [
    { "id": 3, "name": "Bubble Bath", "brand": "OPI", "type": "gel", "shade": "Soft sheer pink", "in_stock": true },
    { "id": 7, "name": "Lincoln Park After Dark", "brand": "OPI", "type": "gel", "shade": "Deep plum", "in_stock": true }
  ],
  "total_found": 2
}
```

---

### `list_available_slots`

**Description:** Return open appointment slots for a given date or date range. Always call this before `book_appointment` to confirm availability. Returns slots in the customer's local time.

**Request parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string | Optional | Specific date in `YYYY-MM-DD` format |
| `date_from` | string | Optional | Start of date range in `YYYY-MM-DD` |
| `date_to` | string | Optional | End of date range in `YYYY-MM-DD` |
| `service_id` | integer | Optional | Filter slots long enough for this service |
| `technician` | string | Optional | Filter by specific technician name |

One of `date` or `date_from`+`date_to` must be provided.

**Response shape:**

| Field | Type | Description |
|-------|------|-------------|
| `slots` | array | Available time slots |
| `slots[].datetime` | string | ISO 8601 datetime of slot start |
| `slots[].technician` | string | Technician name |
| `slots[].duration_available_min` | integer | Available window in minutes |
| `date_queried` | string | Date(s) queried |

**Example request:**

```json
{ "date": "2026-05-21", "service_id": 2 }
```

**Example response:**

```json
{
  "slots": [
    { "datetime": "2026-05-21T10:00:00", "technician": "Lisa",  "duration_available_min": 120 },
    { "datetime": "2026-05-21T14:00:00", "technician": "Jenny", "duration_available_min": 60 },
    { "datetime": "2026-05-21T16:00:00", "technician": "Lisa",  "duration_available_min": 90 }
  ],
  "date_queried": "2026-05-21"
}
```

---

### `book_appointment`

**Description:** Create a new appointment. Requires a confirmed available slot (check `list_available_slots` first). The caller's phone is used to look up or create a customer record.

**Request parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `customer_phone` | string | Yes | Caller's E.164 phone number |
| `customer_name` | string | Yes | Customer's full name |
| `service_id` | integer | Yes | Service ID from `list_services` |
| `datetime` | string | Yes | ISO 8601 datetime for the appointment |
| `technician` | string | No | Preferred technician name or `"Any"` (default: `"Any"`) |
| `notes` | string | No | Any special requests or notes |

**Response shape:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the booking succeeded |
| `appointment_id` | integer | Newly created appointment ID |
| `confirmation` | string | Human-readable confirmation message |
| `error` | string | Error message if `success` is false |

**Example request:**

```json
{
  "customer_phone": "+15551234567",
  "customer_name": "Maria Garcia",
  "service_id": 2,
  "datetime": "2026-05-21T14:00:00",
  "technician": "Jenny",
  "notes": "Please use OPI gel polish"
}
```

**Example response:**

```json
{
  "success": true,
  "appointment_id": 42,
  "confirmation": "Booked! Maria Garcia has a Gel Manicure on Thursday May 21 at 2:00 PM with Jenny. See you then!"
}
```

---

### `modify_appointment`

**Description:** Change the date, time, service, or technician of an existing appointment. Use when a caller wants to reschedule. Verify the new slot is available with `list_available_slots` first.

**Request parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `appointment_id` | integer | Yes | ID of the appointment to modify |
| `datetime` | string | Optional | New ISO 8601 datetime |
| `service_id` | integer | Optional | New service ID |
| `technician` | string | Optional | New preferred technician or `"Any"` |
| `notes` | string | Optional | Updated notes (replaces existing) |

**Response shape:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the modification succeeded |
| `appointment_id` | integer | Appointment ID |
| `confirmation` | string | Human-readable confirmation message |
| `error` | string | Error message if `success` is false |

**Example request:**

```json
{
  "appointment_id": 42,
  "datetime": "2026-05-22T11:00:00",
  "technician": "Lisa"
}
```

**Example response:**

```json
{
  "success": true,
  "appointment_id": 42,
  "confirmation": "Your Gel Manicure has been rescheduled to Friday May 22 at 11:00 AM with Lisa."
}
```

---

### `cancel_appointment`

**Description:** Cancel an existing appointment. Use when a caller explicitly asks to cancel. Confirm the appointment details before cancelling.

**Request parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `appointment_id` | integer | Yes | ID of the appointment to cancel |
| `reason` | string | No | Cancellation reason (stored in notes) |

**Response shape:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the cancellation succeeded |
| `appointment_id` | integer | Appointment ID |
| `confirmation` | string | Human-readable confirmation message |
| `error` | string | Error message if `success` is false |

**Example request:**

```json
{ "appointment_id": 42, "reason": "Schedule conflict" }
```

**Example response:**

```json
{
  "success": true,
  "appointment_id": 42,
  "confirmation": "Your Gel Manicure on May 21 at 2:00 PM has been cancelled. We hope to see you soon!"
}
```

---

### `request_callback`

**Description:** Log a callback request when the salon cannot immediately address a customer's need, or when a customer asks to be called back. Used for complex requests that require human staff.

**Request parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `customer_phone` | string | Yes | Caller's E.164 phone number |
| `customer_name` | string | Yes | Customer's name |
| `reason` | string | Yes | Reason for callback request |
| `preferred_time` | string | No | Customer's preferred callback time (free text) |

**Response shape:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the callback was logged |
| `callback_id` | integer | Callback record ID |
| `confirmation` | string | Human-readable confirmation message |

**Example request:**

```json
{
  "customer_phone": "+15551234567",
  "customer_name": "Maria Garcia",
  "reason": "Wants to ask about bridal party package pricing",
  "preferred_time": "Tomorrow morning before noon"
}
```

**Example response:**

```json
{
  "success": true,
  "callback_id": 9,
  "confirmation": "Got it! Someone from our team will call you back about bridal party packages, preferably before noon tomorrow."
}
```

---

### `hang_up`

**Description:** End the call gracefully. Always call this tool when the conversation is complete — after a booking confirmation, after a goodbye, or when the caller says they have no more questions. Do not call this mid-sentence.

**Request parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `reason` | string | No | Brief reason for hanging up, e.g. `"call_complete"`, `"user_requested"` |

**Response shape:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Always `true` |
| `message` | string | Confirmation that hangup was triggered |

**Example request:**

```json
{ "reason": "call_complete" }
```

**Example response:**

```json
{
  "success": true,
  "message": "Hanging up."
}
```

---

## Owner-Only Tools

These tools are only loaded when the caller's phone matches `OWNER_PHONE`. They expose operational data and management capabilities.

---

### `list_today_appointments`

**Description:** Return all appointments scheduled for today (or a specified date). Used by the owner to review the day's schedule at a glance.

**Request parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string | No | Date in `YYYY-MM-DD` format; defaults to today |

**Response shape:**

| Field | Type | Description |
|-------|------|-------------|
| `date` | string | The queried date |
| `appointments` | array | List of appointment objects |
| `appointments[].id` | integer | Appointment ID |
| `appointments[].time` | string | Time in `HH:MM` format |
| `appointments[].customer_name` | string | Customer name |
| `appointments[].customer_phone` | string | Customer phone |
| `appointments[].service_name` | string | Service name |
| `appointments[].technician` | string | Assigned technician |
| `appointments[].status` | string | Appointment status |
| `total` | integer | Total number of appointments |

**Example request:**

```json
{}
```

**Example response:**

```json
{
  "date": "2026-05-19",
  "appointments": [
    { "id": 38, "time": "10:00", "customer_name": "Sarah Lee",    "customer_phone": "+15559876543", "service_name": "Classic Manicure", "technician": "Jenny", "status": "confirmed" },
    { "id": 39, "time": "11:00", "customer_name": "Maria Garcia",  "customer_phone": "+15551234567", "service_name": "Gel Pedicure",      "technician": "Lisa",  "status": "confirmed" },
    { "id": 40, "time": "14:00", "customer_name": "Priya Sharma",  "customer_phone": "+15554443333", "service_name": "Acrylic Full Set",  "technician": "Jenny", "status": "no_show"   }
  ],
  "total": 3
}
```

---

### `update_appointment_status`

**Description:** Change the status of an appointment. Use to mark appointments as completed, no-show, or re-confirm a cancelled booking. Valid statuses: `confirmed`, `completed`, `cancelled`, `no_show`.

**Request parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `appointment_id` | integer | Yes | Appointment ID |
| `status` | string | Yes | New status: `confirmed`, `completed`, `cancelled`, or `no_show` |

**Response shape:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the update succeeded |
| `appointment_id` | integer | Appointment ID |
| `new_status` | string | The updated status |

**Example request:**

```json
{ "appointment_id": 40, "status": "no_show" }
```

**Example response:**

```json
{
  "success": true,
  "appointment_id": 40,
  "new_status": "no_show"
}
```

---

### `list_pending_callbacks`

**Description:** Return all unresolved callback requests. Use so the owner can review which customers need a return call.

**Request parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Maximum number of results (default: 20) |

**Response shape:**

| Field | Type | Description |
|-------|------|-------------|
| `callbacks` | array | Pending callback records |
| `callbacks[].id` | integer | Callback ID |
| `callbacks[].customer_name` | string | Customer name |
| `callbacks[].customer_phone` | string | Customer phone |
| `callbacks[].reason` | string | Reason for callback |
| `callbacks[].preferred_time` | string \| null | Customer's preferred call time |
| `callbacks[].created_at` | string | ISO 8601 when request was logged |
| `total` | integer | Total pending callbacks |

**Example request:**

```json
{ "limit": 10 }
```

**Example response:**

```json
{
  "callbacks": [
    { "id": 9, "customer_name": "Maria Garcia", "customer_phone": "+15551234567", "reason": "Bridal party package pricing", "preferred_time": "Tomorrow morning before noon", "created_at": "2026-05-19T09:15:00" }
  ],
  "total": 1
}
```

---

### `resolve_callback`

**Description:** Mark a callback request as resolved once the owner has called the customer back. Removes it from the pending list.

**Request parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `callback_id` | integer | Yes | Callback ID to resolve |
| `resolution_note` | string | No | Optional note about the outcome |

**Response shape:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the resolution succeeded |
| `callback_id` | integer | Callback ID |
| `message` | string | Confirmation message |

**Example request:**

```json
{ "callback_id": 9, "resolution_note": "Quoted $200 for bridal party of 4. Customer will call back to book." }
```

**Example response:**

```json
{
  "success": true,
  "callback_id": 9,
  "message": "Callback #9 marked as resolved."
}
```

---

### `trigger_reminder_call`

**Description:** Manually trigger an outbound reminder call for a specific appointment, bypassing the scheduled job. Useful if the automatic reminder failed or needs to be resent.

**Request parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `appointment_id` | integer | Yes | Appointment ID to send a reminder for |

**Response shape:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the Twilio call was initiated |
| `appointment_id` | integer | Appointment ID |
| `call_sid` | string | Twilio call SID for the initiated call |
| `message` | string | Confirmation or error details |

**Example request:**

```json
{ "appointment_id": 42 }
```

**Example response:**

```json
{
  "success": true,
  "appointment_id": 42,
  "call_sid": "CA1234567890abcdef1234567890abcdef",
  "message": "Reminder call initiated to +15551234567."
}
```

---

### `append_appointment_note`

**Description:** Add or update the notes field on an existing appointment. Use to log anything relevant that came up during the call — color preferences, special requests, issues.

**Request parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `appointment_id` | integer | Yes | Appointment ID |
| `note` | string | Yes | Note text to append (will be appended to existing notes with a newline separator, not replace) |

**Response shape:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the note was saved |
| `appointment_id` | integer | Appointment ID |
| `notes` | string | Full updated notes field after append |

**Example request:**

```json
{ "appointment_id": 42, "note": "Customer prefers OPI Bubble Bath for base coat." }
```

**Example response:**

```json
{
  "success": true,
  "appointment_id": 42,
  "notes": "Please use OPI gel polish\nCustomer prefers OPI Bubble Bath for base coat."
}
```
