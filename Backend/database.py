"""SQLite cache: users, repositories, contributions, user_settings."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_FILE = Path(__file__).resolve().parent / "portfolio.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY COLLATE NOCASE,
    name TEXT, bio TEXT, avatar_url TEXT,
    followers INTEGER, following INTEGER, public_repos INTEGER,
    heatmap_source TEXT,
    last_updated TEXT
);
CREATE TABLE IF NOT EXISTS repositories (
    id INTEGER PRIMARY KEY,
    username TEXT COLLATE NOCASE,
    name TEXT, description TEXT, language TEXT,
    stars INTEGER, forks INTEGER, topics TEXT, html_url TEXT,
    is_fork INTEGER, pushed_at TEXT
);
CREATE TABLE IF NOT EXISTS contributions (
    username TEXT COLLATE NOCASE, date TEXT, count INTEGER,
    PRIMARY KEY (username, date)
);
CREATE TABLE IF NOT EXISTS user_settings (
    username TEXT PRIMARY KEY COLLATE NOCASE,
    last_job_description TEXT, last_match_pct INTEGER
);
"""


@contextmanager
def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db() as c:
        cols = [r["name"] for r in c.execute("PRAGMA table_info(users)")]
        if cols and "heatmap_source" not in cols:
            # Table from an older version of this project. It is only a cache, so rebuild it.
            c.executescript("DROP TABLE users; DROP TABLE IF EXISTS repositories; DROP TABLE IF EXISTS contributions;")
        c.executescript(SCHEMA)


def save_bundle(user, repos, days, source):
    """Replace everything cached for one user (profile, repos, contribution days)."""
    login = user["login"]
    now = datetime.now(timezone.utc).isoformat()
    with db() as c:
        c.execute(
            "INSERT OR REPLACE INTO users VALUES (?,?,?,?,?,?,?,?,?)",
            (login, user.get("name") or login, user.get("bio"), user.get("avatar_url"),
             user.get("followers", 0), user.get("following", 0), user.get("public_repos", 0),
             source, now),
        )
        c.execute("DELETE FROM repositories WHERE username = ?", (login,))
        c.executemany(
            "INSERT OR REPLACE INTO repositories VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [(r["id"], login, r["name"], r.get("description"), r.get("language"),
              r.get("stargazers_count", 0), r.get("forks_count", 0),
              json.dumps(r.get("topics") or []), r.get("html_url"),
              int(bool(r.get("fork"))), r.get("pushed_at")) for r in repos],
        )
        c.execute("DELETE FROM contributions WHERE username = ?", (login,))
        c.executemany("INSERT INTO contributions VALUES (?,?,?)", [(login, d, n) for d, n in days])


def load_bundle(username):
    """Return {'user', 'repos', 'days'} from the cache, or None if the user was never cached."""
    with db() as c:
        user = c.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not user:
            return None
        repos = [dict(r) for r in c.execute("SELECT * FROM repositories WHERE username = ?", (username,))]
        days = [(r["date"], r["count"]) for r in
                c.execute("SELECT date, count FROM contributions WHERE username = ? ORDER BY date", (username,))]
    for r in repos:
        r["topics"] = json.loads(r["topics"] or "[]")
    return {"user": dict(user), "repos": repos, "days": days}


def get_settings(username):
    with db() as c:
        row = c.execute("SELECT * FROM user_settings WHERE username = ?", (username,)).fetchone()
    return dict(row) if row else None


def save_match(username, job_description, pct):
    with db() as c:
        c.execute("INSERT OR REPLACE INTO user_settings VALUES (?,?,?)", (username, job_description, pct))
