import re
import sqlite3


def normalize_phone(phone: str) -> str:
    """Normalize a phone number to E.164 format (+1XXXXXXXXXX)."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits[0] == "1":
        return f"+{digits}"
    # Return as-is with + prefix if we can't normalize (still strip non-digits)
    return f"+{digits}"


def upsert_customer(db: sqlite3.Connection, name: str, phone: str) -> int:
    """
    Insert customer if not exists (keyed on normalized phone), then return customer_id.
    """
    normalized = normalize_phone(phone)
    db.execute(
        "INSERT OR IGNORE INTO customers (name, phone) VALUES (?, ?)",
        (name, normalized),
    )
    db.commit()
    row = db.execute(
        "SELECT id FROM customers WHERE phone = ?", (normalized,)
    ).fetchone()
    return row["id"]
