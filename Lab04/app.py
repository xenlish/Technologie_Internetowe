from flask import Flask, jsonify, request, make_response
import sqlite3
from db_initiation import DB_PATH, init_db

app = Flask(__name__, static_folder="static", static_url_path="")

init_db()


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():

    return app.send_static_file("index.html")


@app.route("/api/movies", methods=["GET"])
def get_movies():
    year = request.args.get("year", type=int)
    limit = request.args.get("limit", type=int)

    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT
            m.id,
            m.title,
            m.year,
            IFNULL(ROUND(AVG(r.score), 2), 0) AS avg_score,
            COUNT(r.id) AS votes
        FROM movies m
        LEFT JOIN ratings r ON r.movie_id = m.id
    """
    params = []

    if year:
        query += " WHERE m.year = ?"
        params.append(year)

    query += """
        GROUP BY m.id
        ORDER BY avg_score DESC, votes DESC, m.title ASC
    """

    if limit:
        query += " LIMIT ?"
        params.append(limit)

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    movies = [dict(row) for row in rows]
    return jsonify(movies)


@app.route("/api/movies/top", methods=["GET"])
def get_top_movies():
    # bonus: GET /api/movies/top?limit=5&year=2014
    year = request.args.get("year", type=int)
    limit = request.args.get("limit", default=5, type=int)

    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT
            m.id,
            m.title,
            m.year,
            IFNULL(ROUND(AVG(r.score), 2), 0) AS avg_score,
            COUNT(r.id) AS votes
        FROM movies m
        LEFT JOIN ratings r ON r.movie_id = m.id
    """
    params = []

    if year:
        query += " WHERE m.year = ?"
        params.append(year)

    query += """
        GROUP BY m.id
        ORDER BY avg_score DESC, votes DESC, m.title ASC
        LIMIT ?
    """
    params.append(limit)

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    movies = [dict(row) for row in rows]
    return jsonify(movies)


@app.route("/api/movies", methods=["POST"])
def create_movie():
    if not request.is_json:
        return jsonify({"error": "Expected application/json"}), 400

    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    year = data.get("year")

    if not title:
        return jsonify({"error": "title is required"}), 422

    try:
        year = int(year)
    except (TypeError, ValueError):
        return jsonify({"error": "year must be integer"}), 422

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO movies (title, year) VALUES (?, ?)",
        (title, year),
    )
    movie_id = cur.lastrowid
    conn.commit()
    conn.close()

    resp = make_response({"id": movie_id, "title": title, "year": year}, 201)
    resp.headers["Location"] = f"/api/movies/{movie_id}"
    return resp


@app.route("/api/ratings", methods=["POST"])
def create_rating():
    if not request.is_json:
        return jsonify({"error": "Expected application/json"}), 400

    data = request.get_json() or {}
    movie_id = data.get("movie_id")
    score = data.get("score")

    try:
        movie_id = int(movie_id)
    except (TypeError, ValueError):
        return jsonify({"error": "movie_id must be integer"}), 422

    try:
        score = int(score)
    except (TypeError, ValueError):
        return jsonify({"error": "score must be integer"}), 422

    if not (1 <= score <= 5):
        return jsonify({"error": "score must be between 1 and 5"}), 422

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM movies WHERE id = ?", (movie_id,))
    if cur.fetchone() is None:
        conn.close()
        return jsonify({"error": "movie not found"}), 404

    cur.execute(
        "INSERT INTO ratings (movie_id, score) VALUES (?, ?)",
        (movie_id, score),
    )
    rating_id = cur.lastrowid
    conn.commit()
    conn.close()

    resp = make_response({"id": rating_id}, 201)
    resp.headers["Location"] = f"/api/ratings/{rating_id}"
    return resp

@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


if __name__ == "__main__":
    app.run(debug=True)