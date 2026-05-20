# CLAUDE.md — Morty Frontend Dashboard

## Project Overview

You are building a **management dashboard frontend** for **Morty**, a voice-based AI appointment scheduling system. The frontend sits on top of a SQLite database and communicates with it **exclusively through the FastAPI tool-server's HTTP endpoints** — never via direct SQLite access.

All mutations (booking, modifying, canceling appointments; upserting customers) go through the tool endpoints. All reads also go through the tool endpoints or purpose-built GET routes. Do not introduce any direct DB layer on the frontend side.

---

## Tech Stack

- **Framework**: Next.js (App Router) with TypeScript
- **Styling**: Tailwind CSS
- **State Management**: React Query (TanStack Query) for server state; `useState`/`useReducer` for local UI state
- **Forms**: React Hook Form + Zod for validation
- **Date/Time**: `date-fns` for formatting; native `<input type="datetime-local">` for picking
- **Notifications**: `sonner` (toast library) for success/error feedback
- **Icons**: `lucide-react`

Do not add unnecessary dependencies. Keep the bundle lean.

---

## Backend API Contract

The tool-server runs at `http://localhost:8000`. All requests go to this base URL. Do not hardcode it — read from `NEXT_PUBLIC_API_URL` env variable (default: `http://localhost:8000`).

### Endpoints

#### Appointments

```
POST   /tools/book
Body:  { customer_phone: string, service: string, datetime: string (ISO 8601), duration_min?: number }
Returns: { appointment_id: number, status: "booked", datetime: string, service: string, customer: CustomerObject }

POST   /tools/modify
Body:  { appointment_id: number, changes: { service?: string, datetime?: string, duration_min?: number } }
Returns: { appointment_id: number, status: "modified", updated_fields: string[] }

POST   /tools/cancel
Body:  { appointment_id: number }
Returns: { appointment_id: number, status: "cancelled" }

GET    /tools/availability?date=YYYY-MM-DD
Returns: { date: string, open_slots: string[] }  // ISO datetime strings

GET    /tools/search?q=<name|phone|id>
Returns: { results: AppointmentResult[] }
```

#### Customers

```
GET    /tools/customer?phone=<phone>
Returns: { id: number, name: string, phone: string, notes: string } | { created: true, id: number }
```

---

## Data Types

Define these in `lib/types.ts` and import everywhere:

```ts
export type AppointmentStatus = "booked" | "modified" | "cancelled" | "completed";

export interface Customer {
  id: number;
  name: string;
  phone: string;
  notes?: string;
}

export interface Appointment {
  id: number;
  customer_id: number;
  customer?: Customer;         // joined when returned from search
  service: string;
  datetime: string;            // ISO 8601
  duration_min: number;
  status: AppointmentStatus;
  reminder_sent: boolean;
}

export interface Service {
  id: number;
  name: string;
  duration_min: number;
  price: number;
}

export interface AvailabilityResult {
  date: string;
  open_slots: string[];
}
```

---

## Project Structure

```
morty-dashboard/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                  # redirects to /dashboard
│   └── dashboard/
│       ├── page.tsx              # main calendar + appointment list view
│       ├── appointments/
│       │   └── [id]/page.tsx     # appointment detail / edit
│       ├── customers/
│       │   └── page.tsx          # customer search + detail
│       └── search/
│           └── page.tsx          # global fuzzy search
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   └── Header.tsx
│   ├── appointments/
│   │   ├── AppointmentCard.tsx
│   │   ├── AppointmentList.tsx
│   │   ├── BookingModal.tsx       # form to book new appointment
│   │   ├── ModifyModal.tsx        # form to modify existing
│   │   └── CancelButton.tsx
│   ├── customers/
│   │   ├── CustomerSearch.tsx
│   │   └── CustomerCard.tsx
│   └── ui/
│       └── (shared primitives: Badge, Modal, Spinner, EmptyState)
├── lib/
│   ├── api.ts                    # all fetch wrappers (typed)
│   ├── types.ts                  # shared TypeScript types
│   └── utils.ts                  # date formatting, phone formatting, etc.
├── hooks/
│   ├── useAppointments.ts        # React Query hooks for appointment operations
│   ├── useCustomers.ts
│   └── useAvailability.ts
└── .env.local
    └── NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## API Layer (`lib/api.ts`)

All API calls must be centralized here. Each function must:
1. Call the correct endpoint
2. Throw a descriptive error if the response is not ok
3. Return the typed response

Example pattern:
```ts
export async function bookAppointment(payload: BookPayload): Promise<BookResult> {
  const res = await fetch(`${API_URL}/tools/book`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to book appointment");
  }
  return res.json();
}
```

Do the same for `modifyAppointment`, `cancelAppointment`, `searchAppointments`, `getAvailability`, `getCustomer`.

---

## React Query Hooks (`hooks/`)

Use React Query mutations for all write operations and queries for all reads.

```ts
// Example: useAppointments.ts
export function useBookAppointment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: bookAppointment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
      toast.success("Appointment booked!");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}
```

Invalidate the relevant query keys on every successful mutation so the UI always reflects the latest DB state.

---

## Dashboard Views

### 1. Main Dashboard (`/dashboard`)
- **Today's appointments** list, ordered by time
- Quick stats bar: total booked today, upcoming this week, pending reminders
- **New Appointment** button → opens `BookingModal`
- Each appointment card shows: customer name + phone, service, time, status badge, Edit/Cancel actions

### 2. Booking Modal
- Fields: Customer Phone (auto-looks up or creates customer via `GET /tools/customer`), Service (dropdown), Date picker, then auto-fetch availability for that date via `GET /tools/availability`, Time slot selector from returned slots
- On submit → `POST /tools/book`

### 3. Modify Modal
- Pre-filled with existing appointment data
- Only show fields that can change: service, datetime (with availability re-fetch), duration
- On submit → `POST /tools/modify`

### 4. Search Page (`/dashboard/search`)
- Single search input — queries `GET /tools/search?q=` on debounced input (300ms)
- Renders results as appointment cards with inline Edit/Cancel

### 5. Customer Page (`/dashboard/customers`)
- Phone number lookup → `GET /tools/customer?phone=`
- Shows customer info + all their appointments (from search results filtered by phone)

---

## Critical Rules

1. **Never write to SQLite directly.** All data mutations go through the FastAPI endpoints listed above.
2. **All mutations use the tool endpoints** — `/tools/book`, `/tools/modify`, `/tools/cancel`. Never bypass them.
3. **Invalidate queries after every mutation** so the UI reflects DB state without manual refresh.
4. **Show loading and error states** everywhere — spinners on fetch, toast errors on failure, disabled buttons while mutations are in-flight.
5. **Phone numbers** are the primary customer identifier. Normalize them before sending (strip spaces, dashes; keep `+` prefix if present).
6. **Datetimes** must always be sent as ISO 8601 strings (`2025-05-19T14:30:00`). Use `date-fns` for all formatting/parsing.
7. **Do not add auth** unless explicitly asked. This is an internal ops tool.
8. **Do not add a direct `/appointments` list endpoint** that bypasses the tool layer — use `/tools/search` with a broad query or a purpose-built read endpoint if the tool-server exposes one.

---

## Aesthetic Direction

The dashboard should feel like a **clean, professional internal ops tool** — not a consumer app, not a flashy SaaS landing page. Think:
- Neutral dark sidebar, light content area
- Monospace or semi-monospace accents for IDs, phone numbers, timestamps
- Status badges with clear color coding: green (booked), amber (modified), red (cancelled), gray (completed)
- Dense information layout — this is used by someone managing a calendar, not a casual user
- Minimal animation — only where it aids clarity (e.g., modal open/close, toast slide-in)

---

## Environment

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Add this to `.env.local`. Never commit secrets.

---

## Getting Started Checklist

Claude Code should tackle these in order:

1. Scaffold Next.js project with TypeScript + Tailwind
2. Create `lib/types.ts` with all shared types
3. Create `lib/api.ts` with all fetch wrappers
4. Set up React Query provider in `app/layout.tsx`
5. Build `hooks/useAppointments.ts` and `hooks/useCustomers.ts`
6. Build the Sidebar + Header layout components
7. Build `AppointmentCard` and `AppointmentList`
8. Build `BookingModal` (with availability fetch + slot picker)
9. Build `ModifyModal`
10. Build `CancelButton` with confirmation
11. Wire up `/dashboard` main page
12. Build Search page
13. Build Customer lookup page
14. Add loading/error/empty states throughout
15. Polish: status badges, phone formatting, datetime display