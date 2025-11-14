from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime
from pathlib import Path

app = Flask(__name__, static_folder="static", static_url_path="/")

DB_PATH = Path("instance/shop.db")
DB_PATH.parent.mkdir(exist_ok=True)

cart = {}  


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.before_first_request
def init():
    from db_initiation.py import init_db
    init_db()


@app.after_request
def add_headers(res):
    res.headers.setdefault("Cache-Control", "no-store")
    return res


#UI 

@app.route("/")
def index():
    return app.send_static_file("index.html")


#PRODUCTS 

@app.route("/api/products", methods=["GET"])
def products_list():
    conn = get_db()
    rows = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/products", methods=["POST"])
def product_create():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    price = data.get("price")

    if not name or not isinstance(name, str):
        return jsonify({"error": "Invalid name"}), 400

    try:
        price = float(price)
        if price < 0:
            raise ValueError
    except:
        return jsonify({"error": "Invalid price"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO products(name, price) VALUES(?, ?)", (name, price))
    conn.commit()
    pid = cur.lastrowid
    conn.close()

    return jsonify({"id": pid, "name": name, "price": price}), 201


#CART 

def load_product(pid):
    conn = get_db()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    conn.close()
    return row


@app.route("/api/cart", methods=["GET"])
def cart_get():
    items = []
    total = 0.0

    for pid, qty in cart.items():
        p = load_product(int(pid))
        if not p:
            continue
        line = p["price"] * qty
        total += line
        items.append({
            "product_id": p["id"],
            "name": p["name"],
            "unit_price": p["price"],
            "qty": qty,
            "line_total": line
        })

    return jsonify({"items": items, "total": total})


def validate_qty(data):
    try:
        q = int(data.get("qty"))
        if q <= 0:
            raise ValueError
        return q
    except:
        return None


@app.route("/api/cart/add", methods=["POST"])
def cart_add():
    data = request.get_json(silent=True) or {}
    pid = data.get("product_id")
    qty = validate_qty(data)

    try:
        pid = int(pid)
    except:
        return jsonify({"error": "Invalid product_id"}), 400

    if qty is None:
        return jsonify({"error": "qty must be > 0"}), 400

    if not load_product(pid):
        return jsonify({"error": "Product not found"}), 404

    cart[str(pid)] = cart.get(str(pid), 0) + qty
    return cart_get()


@app.route("/api/cart/item", methods=["PATCH"])
def cart_patch():
    data = request.get_json(silent=True) or {}
    pid = data.get("product_id")
    qty = validate_qty(data)

    try:
        pid = int(pid)
    except:
        return jsonify({"error": "Invalid product_id"}), 400

    if str(pid) not in cart:
        return jsonify({"error": "Item not in cart"}), 404

    if qty is None:
        return jsonify({"error": "qty must be > 0"}), 400

    cart[str(pid)] = qty
    return cart_get()


@app.route("/api/cart/item/<int:pid>", methods=["DELETE"])
def cart_delete(pid):
    if str(pid) not in cart:
        return jsonify({"error": "Not in cart"}), 404
    del cart[str(pid)]
    return cart_get()


# CHEKOUT

@app.route("/api/checkout", methods=["POST"])
def checkout():
    if not cart:
        return jsonify({"error": "Cart empty"}), 400

    conn = get_db()
    cur = conn.cursor()

    cur.execute("INSERT INTO orders(created_at) VALUES(?)", (datetime.utcnow().isoformat(),))
    order_id = cur.lastrowid

    total = 0.0
    for pid, qty in cart.items():
        p = load_product(int(pid))
        if not p:
            continue
        snapshot_price = p["price"]
        line = snapshot_price * qty
        total += line

        cur.execute("""
            INSERT INTO order_items(order_id, product_id, qty, price)
            VALUES(?,?,?,?)
        """, (order_id, pid, qty, snapshot_price))

    conn.commit()
    conn.close()

    cart.clear()

    return jsonify({"order_id": order_id, "total": total}), 201


# ORDERS 

@app.route("/api/orders", methods=["GET"])
def orders_list():
    conn = get_db()
    cur = conn.cursor()

    rows = cur.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    result = []

    for r in rows:
        items_rows = cur.execute("""
            SELECT oi.product_id, p.name, oi.qty, oi.price
            FROM order_items oi
            JOIN products p ON p.id = oi.product_id
            WHERE oi.order_id = ?
        """, (r["id"],)).fetchall()

        items = []
        total = 0.0
        for it in items_rows:
            lt = it["qty"] * it["price"]
            total += lt
            items.append({
                "product_id": it["product_id"],
                "name": it["name"],
                "qty": it["qty"],
                "unit_price_snapshot": it["price"],
                "line_total": lt
            })

        result.append({
            "id": r["id"],
            "created_at": r["created_at"],
            "items": items,
            "total": total
        })

    conn.close()
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)
