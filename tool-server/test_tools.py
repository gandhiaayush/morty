"""
pytest test suite for the Morty nail salon FastAPI tool-server.
All tests use FastAPI's TestClient against a temporary SQLite database.
8 core tests covering the most critical paths only.
"""

import uuid


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _unique_phone() -> str:
    """Return a unique E.164-style phone number for each test."""
    suffix = str(uuid.uuid4().int)[:10]
    return f"+1{suffix}"


def _book(client, phone: str, name: str, service_id: int, dt: str) -> dict:
    """Convenience wrapper: book an appointment and return the full response body."""
    resp = client.post(
        "/tools/book_appointment",
        json={
            "customer_phone": phone,
            "customer_name": name,
            "service_id": service_id,
            "datetime": dt,
        },
    )
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# 1. Health check
# ---------------------------------------------------------------------------

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# 2. Tool schemas — 10 tools, each type == "function"
# ---------------------------------------------------------------------------

def test_get_schemas(client):
    resp = client.get("/tools/schemas")
    assert resp.status_code == 200
    body = resp.json()
    assert "tools" in body
    tools = body["tools"]
    assert len(tools) == 10
    for tool in tools:
        assert tool["type"] == "function"
        assert "name" in tool
        assert "description" in tool
        assert "parameters" in tool


# ---------------------------------------------------------------------------
# 3. Book appointment — full happy path
# ---------------------------------------------------------------------------

def test_book_appointment(client):
    phone = _unique_phone()
    body = _book(client, phone, "Sarah Chen", 3, "2026-06-15T10:00:00")
    assert body["success"] is True
    appt = body["appointment"]
    assert appt["service_name"] == "Gel Manicure"
    assert appt["status"] == "scheduled"


# ---------------------------------------------------------------------------
# 4. Search by name — book for "Diana Patel", search "Diana", assert found
# ---------------------------------------------------------------------------

def test_search_by_name(client):
    phone = _unique_phone()
    _book(client, phone, "Diana Patel", 1, "2026-06-25T09:00:00")

    resp = client.post("/tools/search", json={"query": "Diana"})
    assert resp.status_code == 200
    results = resp.json()["results"]
    customer_entries = [r for r in results if r.get("type") == "customer"]
    names = [r["name"] for r in customer_entries]
    assert "Diana Patel" in names


# ---------------------------------------------------------------------------
# 5. Modify appointment — book -> modify datetime -> assert changed
# ---------------------------------------------------------------------------

def test_modify_appointment(client):
    phone = _unique_phone()
    data = _book(client, phone, "Lily Nguyen", 2, "2026-07-01T09:00:00")
    appt_id = data["appointment"]["id"]

    new_dt = "2026-07-01T11:00:00"
    resp = client.post(
        "/tools/modify_appointment",
        json={"appointment_id": appt_id, "datetime": new_dt},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["appointment"]["datetime"] == new_dt


# ---------------------------------------------------------------------------
# 6. Cancel appointment — book -> cancel -> double-cancel returns error
# ---------------------------------------------------------------------------

def test_cancel_appointment(client):
    phone = _unique_phone()
    data = _book(client, phone, "James Rivera", 4, "2026-07-10T14:00:00")
    appt_id = data["appointment"]["id"]

    r1 = client.post("/tools/cancel_appointment", json={"appointment_id": appt_id})
    assert r1.status_code == 200
    assert r1.json()["success"] is True

    r2 = client.post("/tools/cancel_appointment", json={"appointment_id": appt_id})
    assert r2.status_code == 200
    assert r2.json()["success"] is False


# ---------------------------------------------------------------------------
# 7. Availability blocked — book at 14:00 -> assert that slot unavailable
# ---------------------------------------------------------------------------

def test_get_availability_blocked(client):
    phone = _unique_phone()
    date = "2026-08-05"
    # Gel Manicure (service_id=3) is 60 minutes, booked at 14:00
    _book(client, phone, "Nina Torres", 3, f"{date}T14:00:00")

    resp = client.post(
        "/tools/get_availability",
        json={"date": date, "service_id": 3},
    )
    assert resp.status_code == 200
    slots = resp.json()["slots"]
    slot_map = {s["slot"]: s["available"] for s in slots}
    assert "14:00" in slot_map
    assert slot_map["14:00"] is False


# ---------------------------------------------------------------------------
# 8. Session start and end
# ---------------------------------------------------------------------------

def test_session_start_and_end(client):
    session_id = f"sess-{uuid.uuid4()}"

    start_resp = client.post(
        "/sessions/start",
        json={
            "session_id": session_id,
            "phone": "+16505550202",
            "role": "consumer",
            "started_at": "2026-06-15T10:00:00",
        },
    )
    assert start_resp.status_code == 200
    assert start_resp.json()["ok"] is True

    end_resp = client.post(
        "/sessions/end",
        json={
            "session_id": session_id,
            "ended_at": "2026-06-15T10:02:00",
            "duration_sec": 120,
        },
    )
    assert end_resp.status_code == 200
    assert end_resp.json()["ok"] is True
