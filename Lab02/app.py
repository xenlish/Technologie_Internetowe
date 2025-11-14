from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime, UTC
from pathlib import Path

from db_initiation import init_db

app = Flask(__name__, static_folder="static", static_url_path="/")
app.url_map.strict_slashes = False   

DB_PATH = Path("instance/shop.db")
DB_PATH.parent.mkdir(exist_ok=True)


init_db()


cart = {}
applied_coupon = None  



def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.after_request
def add_headers(res):
    res.headers.setdefault("Cache-Control", "no-store")
    return res


@app.route("/")
def index():
    return app.send_static_file("index.html")



@app.route("/api/products", methods=["GET"])
def products_list():
    conn = get_db()
    rows = conn.execute("SELECT id, name, price FROM products ORDER BY id").fetchall()
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
    except Exception:
        return jsonify({"error": "Invalid price"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO products (name, price) VALUES (?, ?)", (name, price))
    conn.commit()
    product_id = cur.lastrowid
    conn.close()

    return jsonify({"id": product_id, "name": name, "price": price}), 201

def load_product(pid: int):
    conn = get_db()
    row = conn.execute(
        "SELECT id, name, price FROM products WHERE id = ?",
        (pid,)
    ).fetchone()
    conn.close()
    return row


def load_coupon(code: str):
    conn = get_db()
    row = conn.execute(
        "SELECT code, percent FROM coupons WHERE UPPER(code) = UPPER(?)",
        (code,)
    ).fetchone()
    conn.close()
    return row


def compute_cart_summary():
    items = []
    total = 0.0

    for pid, qty in cart.items():
        product = load_product(int(pid))
        if not product:
            continue

        line_total = product["price"] * qty
        total += line_total

        items.append({
            "product_id": product["id"],
            "name": product["name"],
            "unit_price": product["price"],
            "qty": qty,
            "line_total": line_total
        })

    return items, total


def validate_qty(data):
    try:
        q = int(data.get("qty"))
        if q <= 0:
            raise ValueError
        return q
    except Exception:
        return None

@app.route("/api/cart", methods=["GET"])
def cart_get():
    items, total = compute_cart_summary()

    result = {
        "items": items,
        "total": total,
        "coupon": None,
        "total_with_discount": total
    }

    if applied_coupon:
        percent = applied_coupon["percent"]
        discount = total * (percent / 100)
        result["coupon"] = applied_coupon
        result["total_with_discount"] = total - discount

    return jsonify(result)


@app.route("/api/cart/add", methods=["POST"])
def cart_add():
    data = request.get_json(silent=True) or {}

    try:
        pid = int(data.get("product_id"))
    except Exception:
        return jsonify({"error": "Invalid product_id"}), 400

    qty = validate_qty(data)
    if qty is None:
        return jsonify({"error": "qty must be > 0"}), 400

    if not load_product(pid):
        return jsonify({"error": "Product not found"}), 404

    cart[str(pid)] = cart.get(str(pid), 0) + qty

    return cart_get()


@app.route("/api/cart/item", methods=["PATCH"])
def cart_patch():
    data = request.get_json(silent=True) or {}

    try:
        pid = int(data.get("product_id"))
    except Exception:
        return jsonify({"error": "Invalid product_id"}), 400

    qty = validate_qty(data)
    if qty is None:
        return jsonify({"error": "qty must be > 0"}), 400

    if str(pid) not in cart:
        return jsonify({"error": "Item not in cart"}), 404

    cart[str(pid)] = qty

    return cart_get()


@app.route("/api/cart/item/<int:pid>", methods=["DELETE"])
def cart_delete(pid):
    if str(pid) not in cart:
        return jsonify({"error": "Item not in cart"}), 404

    del cart[str(pid)]
    return cart_get()

@app.route("/api/cart/apply-coupon", methods=["POST"])
@app.route("/api/cart/apply-coupon/", methods=["POST"])  # <- ratuje przed 405
def cart_apply_coupon():
    """
    Body: { "code": "PROMO10" }
    """
    global applied_coupon

    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()

    if not code:
        return jsonify({"error": "Coupon code is required"}), 400

    coupon = load_coupon(code)

    if not coupon:
        applied_coupon = None
        return jsonify({"error": "Coupon not found"}), 404

    applied_coupon = {"code": coupon["code"], "percent": coupon["percent"]}

    items, total = compute_cart_summary()
    percent = applied_coupon["percent"]
    total_after = total - (total * percent / 100)

    return jsonify({
        "items": items,
        "total": total,
        "coupon": applied_coupon,
        "total_with_discount": total_after
    })


@app.route("/api/checkout", methods=["POST"])
def checkout():
    global applied_coupon

    if not cart:
        return jsonify({"error": "Cart empty"}), 400

    items, total = compute_cart_summary()

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO orders (created_at) VALUES (?)",
        (datetime.now(UTC).isoformat(),)
    )
    order_id = cur.lastrowid

    for item in items:
        cur.execute("""
            INSERT INTO order_items (order_id, product_id, qty, price)
            VALUES (?, ?, ?, ?)
        """, (order_id, item["product_id"], item["qty"], item["unit_price"]))

    conn.commit()
    conn.close()

    total_to_pay = total
    if applied_coupon:
        total_to_pay = total * (1 - applied_coupon["percent"] / 100)

    cart.clear()
    applied_coupon = None

    return jsonify({
        "order_id": order_id,
        "total": total_to_pay
    }), 201


@app.route("/api/orders", methods=["GET"])
def orders_list():
    conn = get_db()
    cur = conn.cursor()

    rows = cur.execute("SELECT id, created_at FROM orders ORDER BY id DESC").fetchall()

    result = []
    for r in rows:
        items_rows = cur.execute("""
            SELECT oi.product_id, p.name, oi.qty, oi.price
            FROM order_items oi
            JOIN products p ON p.id = oi.product_id
            WHERE oi.order_id = ?
        """, (r["id"],)).fetchall()

        order_items = []
        total = 0

        for it in items_rows:
            line_total = it["qty"] * it["price"]
            total += line_total

            order_items.append({
                "product_id": it["product_id"],
                "name": it["name"],
                "qty": it["qty"],
                "unit_price_snapshot": it["price"],
                "line_total": line_total
            })

        result.append({
            "id": r["id"],
            "created_at": r["created_at"],
            "items": order_items,
            "total": total
        })

    conn.close()
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)
