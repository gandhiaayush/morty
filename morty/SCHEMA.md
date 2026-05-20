# Morty Database Schema

SQLite database file: `morty.db`

---

## CREATE TABLE Statements

### `customers`

```sql
CREATE TABLE IF NOT EXISTS customers (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    phone      TEXT    NOT NULL UNIQUE,
    email      TEXT,
    notes      TEXT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers (phone);
```

### `services`

```sql
CREATE TABLE IF NOT EXISTS services (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL UNIQUE,
    price        REAL    NOT NULL,
    duration_min INTEGER NOT NULL,
    description  TEXT,
    available    INTEGER NOT NULL DEFAULT 1  -- boolean: 1=true, 0=false
);
```

### `inventory`

```sql
CREATE TABLE IF NOT EXISTS inventory (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT    NOT NULL,
    brand    TEXT    NOT NULL,
    type     TEXT    NOT NULL CHECK(type IN ('regular', 'gel', 'acrylic', 'dip')),
    shade    TEXT,
    in_stock INTEGER NOT NULL DEFAULT 1  -- boolean: 1=true, 0=false
);
```

### `appointments`

```sql
CREATE TABLE IF NOT EXISTS appointments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id     INTEGER NOT NULL REFERENCES customers(id),
    service_id      INTEGER NOT NULL REFERENCES services(id),
    datetime        TEXT    NOT NULL,  -- ISO 8601: 'YYYY-MM-DDTHH:MM:SS'
    duration_min    INTEGER NOT NULL,
    technician      TEXT    NOT NULL DEFAULT 'Any',
    status          TEXT    NOT NULL DEFAULT 'confirmed'
                            CHECK(status IN ('confirmed', 'completed', 'cancelled', 'no_show')),
    notes           TEXT,
    reminder_sent   INTEGER NOT NULL DEFAULT 0,  -- boolean: 1=true, 0=false
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_appointments_datetime    ON appointments (datetime);
CREATE INDEX IF NOT EXISTS idx_appointments_customer_id ON appointments (customer_id);
CREATE INDEX IF NOT EXISTS idx_appointments_status      ON appointments (status);
```

### `callbacks`

```sql
CREATE TABLE IF NOT EXISTS callbacks (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id      INTEGER REFERENCES customers(id),
    customer_name    TEXT    NOT NULL,
    customer_phone   TEXT    NOT NULL,
    reason           TEXT    NOT NULL,
    preferred_time   TEXT,
    resolved         INTEGER NOT NULL DEFAULT 0,  -- boolean: 1=true, 0=false
    resolution_note  TEXT,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now')),
    resolved_at      TEXT
);

CREATE INDEX IF NOT EXISTS idx_callbacks_resolved ON callbacks (resolved);
```

### `sessions`

```sql
CREATE TABLE IF NOT EXISTS sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT    NOT NULL UNIQUE,  -- AssemblyAI session_id from session.ready
    phone        TEXT    NOT NULL,
    role         TEXT    NOT NULL CHECK(role IN ('consumer', 'owner')),
    started_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    ended_at     TEXT,
    duration_sec INTEGER
);

CREATE INDEX IF NOT EXISTS idx_sessions_phone      ON sessions (phone);
CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions (started_at);
```

---

## Entity-Relationship Diagram

```
┌──────────────┐        ┌───────────────────┐        ┌─────────────┐
│  customers   │        │   appointments    │        │  services   │
│──────────────│        │───────────────────│        │─────────────│
│ id      (PK) │◄───────│ customer_id  (FK) │        │ id     (PK) │
│ name         │  1   N │ service_id   (FK) │───────►│ name        │
│ phone   (UQ) │        │ id          (PK)  │  N   1 │ price       │
│ email        │        │ datetime          │        │ duration_min│
│ notes        │        │ duration_min      │        │ description │
│ created_at   │        │ technician        │        │ available   │
└──────────────┘        │ status            │        └─────────────┘
                        │ notes             │
                        │ reminder_sent     │
                        │ created_at        │
                        │ updated_at        │
                        └───────────────────┘

┌──────────────┐        ┌───────────────────┐
│  customers   │        │    callbacks      │
│──────────────│        │───────────────────│
│ id      (PK) │◄───────│ customer_id  (FK) │
│  ...         │  1   N │ id          (PK)  │
└──────────────┘        │ customer_name     │
                        │ customer_phone    │
                        │ reason            │
                        │ preferred_time    │
                        │ resolved          │
                        │ resolution_note   │
                        │ created_at        │
                        │ resolved_at       │
                        └───────────────────┘

┌──────────────┐        ┌───────────────────┐
│  inventory   │        │    sessions       │
│──────────────│        │───────────────────│
│ id      (PK) │        │ id          (PK)  │
│ name         │        │ session_id   (UQ) │
│ brand        │        │ phone             │
│ type         │        │ role              │
│ shade        │        │ started_at        │
│ in_stock     │        │ ended_at          │
└──────────────┘        │ duration_sec      │
                        └───────────────────┘
```

---

## Column Descriptions

### `customers`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Auto-incrementing primary key |
| `name` | TEXT | Customer's full name |
| `phone` | TEXT | E.164 phone number, unique across all customers |
| `email` | TEXT | Optional email address |
| `notes` | TEXT | Free-text staff notes (allergies, preferences, history) |
| `created_at` | TEXT | ISO 8601 timestamp of when record was first created |

### `services`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Auto-incrementing primary key |
| `name` | TEXT | Service name, unique |
| `price` | REAL | Price in USD |
| `duration_min` | INTEGER | Typical service duration in minutes |
| `description` | TEXT | Description shown to callers |
| `available` | INTEGER | Boolean (1/0); set to 0 to hide a service without deleting it |

### `inventory`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Auto-incrementing primary key |
| `name` | TEXT | Color or product name |
| `brand` | TEXT | Brand name (e.g. OPI, Essie, CND, Gelish) |
| `type` | TEXT | One of: `regular`, `gel`, `acrylic`, `dip` |
| `shade` | TEXT | Human-readable color description |
| `in_stock` | INTEGER | Boolean (1/0); set to 0 when color runs out |

### `appointments`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Auto-incrementing primary key |
| `customer_id` | INTEGER | FK → `customers.id` |
| `service_id` | INTEGER | FK → `services.id` |
| `datetime` | TEXT | ISO 8601 appointment start time |
| `duration_min` | INTEGER | Duration copied from service at booking time (preserved if service changes) |
| `technician` | TEXT | Assigned technician name or `"Any"` |
| `status` | TEXT | `confirmed`, `completed`, `cancelled`, or `no_show` |
| `notes` | TEXT | Free-text notes (special requests, color preferences) |
| `reminder_sent` | INTEGER | Boolean (1/0); set to 1 after reminder call is placed |
| `created_at` | TEXT | ISO 8601 timestamp when appointment was created |
| `updated_at` | TEXT | ISO 8601 timestamp of last update |

### `callbacks`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Auto-incrementing primary key |
| `customer_id` | INTEGER | FK → `customers.id` (nullable for unknown callers) |
| `customer_name` | TEXT | Name as provided by the caller |
| `customer_phone` | TEXT | Phone as provided by caller (for return call) |
| `reason` | TEXT | Why the caller wants a callback |
| `preferred_time` | TEXT | Free-text preferred callback time |
| `resolved` | INTEGER | Boolean (1/0); set to 1 when staff has called back |
| `resolution_note` | TEXT | Optional staff note about outcome |
| `created_at` | TEXT | ISO 8601 timestamp when callback was requested |
| `resolved_at` | TEXT | ISO 8601 timestamp when marked resolved |

### `sessions`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Auto-incrementing primary key |
| `session_id` | TEXT | AssemblyAI `session_id` from `session.ready`; unique |
| `phone` | TEXT | Caller's E.164 phone number |
| `role` | TEXT | `consumer` or `owner` |
| `started_at` | TEXT | ISO 8601 timestamp when session was opened |
| `ended_at` | TEXT | ISO 8601 timestamp when session closed (null until then) |
| `duration_sec` | INTEGER | Call duration in seconds (computed at session end) |

---

## Seed Data

### Services (8 rows)

```sql
INSERT INTO services (name, price, duration_min, description, available) VALUES
  ('Classic Manicure',  25.00, 30,  'Nail shaping, cuticle care, and regular polish application',          1),
  ('Gel Manicure',      45.00, 45,  'Long-lasting gel polish with UV cure. Lasts 2–3 weeks.',              1),
  ('Classic Pedicure',  35.00, 45,  'Foot soak, nail shaping, massage, and regular polish',                1),
  ('Gel Pedicure',      55.00, 60,  'Full pedicure with long-lasting gel polish',                          1),
  ('Acrylic Full Set',  65.00, 90,  'Full set of acrylic nail extensions with your choice of polish',      1),
  ('Acrylic Fill',      35.00, 60,  'Two-week maintenance fill for existing acrylic nails',                1),
  ('Nail Art (per nail)', 5.00,  5, 'Custom hand-painted nail art design, priced per nail',               1),
  ('Polish Change',     15.00, 20,  'Remove existing polish and apply a fresh color of your choice',       1);
```

### Inventory — OPI Gel Colors (10 rows)

```sql
INSERT INTO inventory (name, brand, type, shade, in_stock) VALUES
  ('Bubble Bath',                  'OPI', 'gel', 'Soft sheer pink — barely-there nude',              1),
  ('Big Apple Red',                'OPI', 'gel', 'Classic vivid red',                                1),
  ('Lincoln Park After Dark',      'OPI', 'gel', 'Deep rich plum, nearly black',                    1),
  ('Funny Bunny',                  'OPI', 'gel', 'Crisp opaque white',                              1),
  ('Malaga Wine',                  'OPI', 'gel', 'Deep burgundy wine',                              1),
  ('You Are So Opal-escent!',      'OPI', 'gel', 'Shimmery opalescent pink',                        1),
  ('Tangerine Dream',              'OPI', 'gel', 'Bright warm coral orange',                        1),
  ('Do You Have This Color in Stock-holm?', 'OPI', 'gel', 'Cool-toned medium pink',                 1),
  ('Midnight in Moscow',           'OPI', 'gel', 'Deep navy blue',                                  0),
  ('Alpine Snow',                  'OPI', 'gel', 'Pure bright white',                               1);
```

### Sample customers and appointments (for development/testing)

```sql
INSERT INTO customers (name, phone, email, notes) VALUES
  ('Maria Garcia',  '+15551234567', 'maria@example.com',  'Prefers OPI. Allergic to acetone-based removers.'),
  ('Sarah Lee',     '+15559876543', 'sarah@example.com',  'Regular every 2 weeks. Loves nail art.'),
  ('Priya Sharma',  '+15554443333', NULL,                 'New customer as of May 2026.');

INSERT INTO appointments (customer_id, service_id, datetime, duration_min, technician, status) VALUES
  (1, 2, '2026-05-21T14:00:00', 45, 'Jenny', 'confirmed'),
  (2, 1, '2026-05-21T10:00:00', 30, 'Lisa',  'confirmed'),
  (3, 5, '2026-05-21T11:30:00', 90, 'Jenny', 'confirmed');
```

---

## Index Recommendations

| Index | Table | Columns | Reason |
|-------|-------|---------|--------|
| `idx_customers_phone` | `customers` | `phone` | Every inbound call looks up the caller by phone number |
| `idx_appointments_datetime` | `appointments` | `datetime` | Slot availability checks and reminder scheduler query by date range |
| `idx_appointments_customer_id` | `appointments` | `customer_id` | Retrieve a customer's appointment history efficiently |
| `idx_appointments_status` | `appointments` | `status` | Filter for active (`confirmed`) appointments only |
| `idx_callbacks_resolved` | `callbacks` | `resolved` | Owner queries always filter for `resolved=0` (pending only) |
| `idx_sessions_phone` | `sessions` | `phone` | Analytics queries group calls by phone number |
| `idx_sessions_started_at` | `sessions` | `started_at` | Time-range queries for call volume reporting |
