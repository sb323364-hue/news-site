import sqlite3
import json
from datetime import datetime

DB_PATH = "news.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS news (
            id TEXT PRIMARY KEY,
            title TEXT,
            url TEXT,
            source TEXT,
            summary TEXT,
            created_at TEXT,
            words TEXT,
            category TEXT
        );
        CREATE TABLE IF NOT EXISTS ratings (
            news_id TEXT PRIMARY KEY,
            rating INTEGER,
            rated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS importance_model (
            word TEXT PRIMARY KEY,
            weight REAL
        );
    """)
    conn.commit()
    conn.close()

def save_news(items):
    conn = get_conn()
    for item in items:
        conn.execute(
            "INSERT OR IGNORE INTO news (id,title,url,source,summary,created_at,words,category) VALUES (?,?,?,?,?,?,?,?)",
            (item["id"], item["title"], item["url"], item["source"],
             item.get("summary",""), datetime.utcnow().isoformat(),
             json.dumps(item.get("words", [])),
             item.get("category",""))
        )
    conn.commit()
    conn.close()

def get_news(limit=60):
    conn = get_conn()
    rows = conn.execute(
        "SELECT n.*, r.rating FROM news n LEFT JOIN ratings r ON n.id=r.news_id "
        "ORDER BY n.created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def set_rating(news_id, rating):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO ratings (news_id, rating, rated_at) VALUES (?,?,?)",
        (news_id, rating, datetime.utcnow().isoformat())
    )
    row = conn.execute("SELECT words FROM news WHERE id=?", (news_id,)).fetchone()
    if row:
        words = json.loads(row["words"])
        for w in words:
            conn.execute(
                "INSERT INTO importance_model (word, weight) VALUES (?, ?) "
                "ON CONFLICT(word) DO UPDATE SET weight = weight + ?",
                (w, rating, rating)
            )
    conn.commit()
    conn.close()

def predict_importance(words):
    conn = get_conn()
    rows = conn.execute("SELECT word, weight FROM importance_model").fetchall()
    conn.close()
    weights = {r["word"]: r["weight"] for r in rows}
    if not weights:
        return 0
    score = sum(weights.get(w, 0) for w in words)
    return score / max(len(words), 1)

def count_ratings():
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) as c FROM ratings").fetchone()
    conn.close()
    return row["c"]
