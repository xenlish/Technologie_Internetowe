import sqlite3
from pathlib import Path

DB_PATH = Path("instance/shop.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL CHECK (price >= 0)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            qty INTEGER NOT NULL CHECK (qty > 0),
            price REAL NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            percent REAL NOT NULL CHECK (percent > 0 AND percent <= 100)
        );
    """)

    cur.execute("SELECT COUNT(*) FROM coupons")
    count = cur.fetchone()[0]

    if count == 0:
        cur.executemany(
            "INSERT INTO coupons(code, percent) VALUES (?, ?)",
            [
                ("PROMO10", 10),
                ("PROMO20", 20),
                ("STUDENT5", 5),
            ]
        )

    conn.commit()
    conn.close()
