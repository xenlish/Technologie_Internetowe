import os
import sqlite3

DB_PATH = "movies.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    if os.path.exists(DB_PATH):
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            year INTEGER NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER NOT NULL,
            score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 5),
            FOREIGN KEY (movie_id) REFERENCES movies(id)
        );
    """)

    cur.executemany(
        "INSERT INTO movies (title, year) VALUES (?, ?)",
        [
            ("Inception", 2010),
            ("Coco", 2021),
            ("Miły Dinozaur", 2023),
            ("Harry Potter", 2015),
        ],
    )

    cur.executemany(
        "INSERT INTO ratings (movie_id, score) VALUES (?, ?)",
        [
            (1, 5), (1, 4), (1, 5),
            (2, 5), (2, 5), (2, 4),
            (3, 5), (3, 4),
            (4, 4), (4, 4), (4, 5),
        ],
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
