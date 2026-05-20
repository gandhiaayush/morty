from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3

from database import get_db

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_service(row) -> dict:
    return {
        "name": row["name"],
        "category": row["category"],
        "price_dollars": row["price_cents"] / 100.0,
        "duration_minutes": row["duration_minutes"],
        "description": row["description"],
    }


def _row_to_color(row) -> dict:
    return {
        "color_name": row["color_name"],
        "brand": row["brand"],
        "in_stock": bool(row["in_stock"]),
    }


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CheckServiceRequest(BaseModel):
    service_name: str


class CheckInventoryRequest(BaseModel):
    color_name: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/list_services")
def list_services(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute(
        "SELECT name, category, price_cents, duration_minutes, description FROM services ORDER BY category, name"
    ).fetchall()
    return {"services": [_row_to_service(r) for r in rows]}


@router.post("/check_service")
def check_service(body: CheckServiceRequest, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute(
        "SELECT name, category, price_cents, duration_minutes, description FROM services WHERE LOWER(name) = LOWER(?)",
        (body.service_name,),
    ).fetchone()
    if row is None:
        return {"found": False, "service": None}
    return {"found": True, "service": _row_to_service(row)}


@router.post("/check_inventory")
def check_inventory(body: CheckInventoryRequest, db: sqlite3.Connection = Depends(get_db)):
    # Exact / case-insensitive match first
    row = db.execute(
        "SELECT color_name, brand, in_stock FROM inventory WHERE LOWER(color_name) LIKE LOWER(?)",
        (f"%{body.color_name}%",),
    ).fetchone()

    if row is None:
        # No match at all — find up to 3 in-stock alternatives from any brand
        alternatives = db.execute(
            "SELECT color_name, brand, in_stock FROM inventory WHERE in_stock = 1 LIMIT 3"
        ).fetchall()
        return {
            "found": False,
            "in_stock": None,
            "color_name": None,
            "brand": None,
            "alternatives": [_row_to_color(r) for r in alternatives],
        }

    found_color = _row_to_service_color(row)
    brand = row["brand"]

    # Build alternatives: up to 3 in-stock colors from same brand (excluding this color),
    # fall back to any brand if fewer than 3.
    if brand:
        same_brand = db.execute(
            "SELECT color_name, brand, in_stock FROM inventory "
            "WHERE in_stock = 1 AND LOWER(brand) = LOWER(?) AND LOWER(color_name) != LOWER(?) LIMIT 3",
            (brand, row["color_name"]),
        ).fetchall()
    else:
        same_brand = []

    if len(same_brand) < 3:
        needed = 3 - len(same_brand)
        existing_names = [r["color_name"] for r in same_brand] + [row["color_name"]]
        placeholders = ",".join("?" * len(existing_names))
        others = db.execute(
            f"SELECT color_name, brand, in_stock FROM inventory "
            f"WHERE in_stock = 1 AND color_name NOT IN ({placeholders}) LIMIT ?",
            (*existing_names, needed),
        ).fetchall()
        alternatives = list(same_brand) + list(others)
    else:
        alternatives = list(same_brand)

    return {
        "found": True,
        "in_stock": bool(row["in_stock"]),
        "color_name": row["color_name"],
        "brand": row["brand"],
        "alternatives": [_row_to_color(r) for r in alternatives],
    }


def _row_to_service_color(row) -> dict:
    return {
        "color_name": row["color_name"],
        "brand": row["brand"],
        "in_stock": bool(row["in_stock"]),
    }
