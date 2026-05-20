import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from database import get_conn


def search(query: str) -> dict:
    results = []

    with get_conn() as conn:
        try:
            q = int(query.strip())
            rows = conn.execute(
                """SELECT a.*, c.name AS customer_name, c.phone AS customer_phone
                   FROM appointments a
                   LEFT JOIN customers c ON c.id = a.customer_id
                   WHERE a.id BETWEEN ? AND ?""",
                (q - 2, q + 2),
            ).fetchall()

            for row in rows:
                results.append({"type": "appointment", **dict(row)})

        except ValueError:
            customers = conn.execute(
                "SELECT id, name, phone, notes FROM customers WHERE name LIKE ? OR phone LIKE ?",
                (f"%{query}%", f"%{query}%"),
            ).fetchall()

            now = datetime.now(timezone.utc).isoformat()

            for cust in customers:
                entry = {"type": "customer", **dict(cust), "appointments": []}

                appts = conn.execute(
                    """SELECT * FROM appointments
                       WHERE customer_id = ? AND status = 'scheduled' AND datetime >= ?
                       ORDER BY datetime ASC""",
                    (cust["id"], now),
                ).fetchall()

                entry["appointments"] = [dict(a) for a in appts]
                results.append(entry)

    return {"results": results}
