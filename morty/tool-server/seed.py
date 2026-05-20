from database import get_db


SERVICES = [
    ("Basic Manicure", "Manicure", 2500, 30),
    ("Gel Manicure", "Manicure", 4000, 45),
    ("Acrylic Full Set", "Manicure", 6500, 90),
    ("Acrylic Fill", "Manicure", 4500, 60),
    ("Basic Pedicure", "Pedicure", 3500, 45),
    ("Spa Pedicure", "Pedicure", 5500, 60),
    ("Nail Art (per nail)", "Nail Art", 500, 15),
    ("French Tips", "Manicure", 1000, 20),
]

INVENTORY = [
    ("Ballet Slipper Pink", "OPI", "#F4A7B9", 1),
    ("Midnight Black", "OPI", "#1A1A1A", 1),
    ("Nude Beige", "Essie", "#C8A882", 1),
    ("Red Red Red", "CND", "#CC0000", 1),
    ("Ocean Blue", "OPI", "#006994", 0),
    ("Lavender Dream", "Essie", "#B57EDC", 1),
    ("Classic Red", "OPI", "#B22222", 1),
    ("Rose Gold", "CND", "#B76E79", 0),
    ("Clear Top Coat", "OPI", "#F5F5F5", 1),
    ("White Snow", "Essie", "#FFFAFA", 1),
]


def seed_if_empty():
    conn = get_db()
    try:
        service_count = conn.execute("SELECT COUNT(*) FROM services").fetchone()[0]
        if service_count == 0:
            conn.executemany(
                "INSERT INTO services (name, category, price_cents, duration_minutes) VALUES (?, ?, ?, ?)",
                SERVICES,
            )
            print(f"[seed] Inserted {len(SERVICES)} services.")

        inventory_count = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        if inventory_count == 0:
            conn.executemany(
                "INSERT INTO inventory (color_name, brand, hex_code, in_stock) VALUES (?, ?, ?, ?)",
                INVENTORY,
            )
            print(f"[seed] Inserted {len(INVENTORY)} inventory items.")

        conn.commit()
    finally:
        conn.close()
