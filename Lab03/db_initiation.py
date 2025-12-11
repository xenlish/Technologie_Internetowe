import sqlite3
from datetime import datetime

DB_PATH = "blog.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("DROP TABLE IF EXISTS comments;")
    c.execute("DROP TABLE IF EXISTS posts;")

    c.execute("""
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)

    c.execute("""
        CREATE TABLE comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            author TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL,
            approved INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        );
    """)

    now = datetime.utcnow().isoformat()

    c.execute("INSERT INTO posts (title, body, created_at) VALUES (?, ?, ?)",
              ("Dlaczego mój kod działa? (A dlaczego nie działa wtedy, kiedy musi?)", 
               "Jest taki moment w życiu każdego programisty, kiedy pisze kod, uruchamia go… i działa.\n"
                "Bez błędów. Bez krzyków. Bez płaczu.\n"
                "To jest podejrzane.\n"
                "Najgorsze jest to, że kiedy później coś poprawiasz — nawet przecinek — aplikacja nagle eksploduje jakby miała wbudowany system wykrywania szczęścia.\n"
                "Debugowanie wygląda wtedy mniej więcej tak:\n"
                "„To na pewno moja wina.”\n"
                "„Jednak nie, coś jest nie tak z biblioteką.”\n"
                "„Może komputer?”\n"
                "„A może… wszechświat?”\n"
                "„O, znalazłam literówkę w zmiennej.”\n"
                "Morał?\n"
                "Jeśli Twój kod działa od razu — nie ciesz się za wcześnie.\n"
                "To tylko chwilowe zawieszenie broni.", '25.11.2025 13:09:22'))

    c.execute("INSERT INTO posts (title, body, created_at) VALUES (?, ?, ?)",
              ("Co bym powiedziała sobie 5 lat temu?", 
               "Nie musisz mieć wszystkiego.\n"
              "Najważniejsze jest robić małe kroki, ale regularnie\n"
              "W poście - rzeczy, które chciałabym zrozumieć dużo wcześniej.\n", now))

    c.executemany("""
        INSERT INTO comments (post_id, author, body, created_at, approved)
        VALUES (?, ?, ?, ?, ?)
    """, [
        (1, "Ola", "Super wpis!", '25.11.2025, 18:12:45', 1),
        (1, "Anonim", "Czekam na więcej!", now, 0),
        (2, "Kasia", "Fajne!", now, 1),
    ])

    conn.commit()
    conn.close()
    print("Baza blog.db została zainicjalizowana.")

if __name__ == "__main__":
    init_db()
