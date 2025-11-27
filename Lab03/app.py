# app.py
from flask import Flask, request, jsonify, send_from_directory
import sqlite3
from datetime import datetime
import os

DB_PATH = "blog.db"

app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/static"
)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index_page():
    return send_from_directory("static", "index.html")


@app.route("/posts/<int:post_id>")
def post_page(post_id):
    # jedna statyczna strona, JS sam odczyta ID z URL
    return send_from_directory("static", "post.html")


@app.route("/moderation")
def moderation_page():
    return send_from_directory("static", "moderation.html")


@app.get("/api/posts")
def list_posts():
    conn = get_db_connection()
    posts = conn.execute(
        "SELECT id, title, body, created_at FROM posts ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(p) for p in posts])


@app.post("/api/posts")
def create_post():
    data = request.get_json(force=True)
    title = data.get("title", "").strip()
    body = data.get("body", "").strip()

    if not title or not body:
        return jsonify({"error": "title and body are required"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute(
        "INSERT INTO posts (title, body, created_at) VALUES (?, ?, ?)",
        (title, body, now)
    )
    post_id = cur.lastrowid
    conn.commit()
    conn.close()

    return jsonify({"id": post_id, "title": title, "body": body, "created_at": now}), 201

@app.get("/api/posts/<int:post_id>/comments")
def list_approved_comments(post_id):
    conn = get_db_connection()
    comments = conn.execute("""
        SELECT id, post_id, author, body, created_at, approved
        FROM comments
        WHERE post_id = ? AND approved = 1
        ORDER BY created_at ASC
    """, (post_id,)).fetchall()
    conn.close()
    return jsonify([dict(c) for c in comments])


@app.post("/api/posts/<int:post_id>/comments")
def create_comment(post_id):
    data = request.get_json(force=True)
    author = data.get("author", "").strip() or "Anonim"
    body = data.get("body", "").strip()

    if not body:
        return jsonify({"error": "body is required"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute("""
        INSERT INTO comments (post_id, author, body, created_at, approved)
        VALUES (?, ?, ?, ?, 0)
    """, (post_id, author, body, now))
    comment_id = cur.lastrowid
    conn.commit()
    conn.close()

   
    return jsonify({"id": comment_id, "approved": 0}), 201



@app.get("/api/comments/pending")
def list_pending_comments():
    conn = get_db_connection()
    comments = conn.execute("""
        SELECT c.id, c.post_id, p.title AS post_title,
               c.author, c.body, c.created_at, c.approved
        FROM comments c
        JOIN posts p ON p.id = c.post_id
        WHERE c.approved = 0
        ORDER BY c.created_at ASC
    """).fetchall()
    conn.close()
    return jsonify([dict(c) for c in comments])


@app.post("/api/comments/<int:comment_id>/approve")
def approve_comment(comment_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE comments SET approved = 1 WHERE id = ?", (comment_id,))
    if cur.rowcount == 0:
        conn.close()
        return jsonify({"error": "comment not found"}), 404
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        from db_initiation import init_db
        init_db()

    app.run(debug=True)
