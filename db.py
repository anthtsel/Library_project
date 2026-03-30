"""
SQLite data layer for the Personal Library app.

All reads and writes go through this module.
`load_books()` and `save_books()` keep the same list-of-dicts interface as the
old JSON layer so that library_logic.py (and the CLI) require no logic changes.

Direct-write functions (db_add_book, db_update_book, db_delete_book) are used
by api.py to avoid the expensive load-all → modify → save-all cycle.
"""

import datetime
import difflib
import json
import os
import shutil
import sqlite3

from config import DATA_FOLDER, DB_FILE

# ── Connection ────────────────────────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db():
    """Create the books table and indexes if they don't exist yet."""
    os.makedirs(DATA_FOLDER, exist_ok=True)
    with get_conn() as conn:
        conn.execute("PRAGMA journal_mode=WAL")   # persistent setting; only needs to run once
        conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                title        TEXT    NOT NULL,
                author       TEXT    NOT NULL,
                genre        TEXT    NOT NULL DEFAULT 'n/a',
                tags         TEXT    NOT NULL DEFAULT '[]',
                status       TEXT    NOT NULL DEFAULT 'Want to Read',
                rating       INTEGER NOT NULL DEFAULT 0,
                blurb        TEXT    NOT NULL DEFAULT '',
                notes        TEXT    NOT NULL DEFAULT '',
                event        TEXT    NOT NULL DEFAULT 'manual',
                timestamp    TEXT,
                last_updated TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_books_status ON books(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_books_title  ON books(title COLLATE NOCASE)")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["tags"] = json.loads(d["tags"]) if d.get("tags") else []
    return d


def _book_params(b: dict) -> dict:
    """Flatten a book dict to the column values expected by INSERT/UPDATE."""
    return {
        "title":        b.get("title", ""),
        "author":       b.get("author", ""),
        "genre":        b.get("genre", "n/a"),
        "tags":         json.dumps(b.get("tags", [])),
        "status":       b.get("status", "Want to Read"),
        "rating":       int(b.get("rating") or 0),
        "blurb":        b.get("blurb", ""),
        "notes":        b.get("notes", ""),
        "event":        b.get("event", "manual"),
        "timestamp":    b.get("timestamp") or datetime.datetime.now().isoformat(),
        "last_updated": b.get("last_updated") or datetime.datetime.now().isoformat(),
    }


_MAX_BACKUPS = 10

def _backup_db():
    """Copy the current DB file with a timestamp suffix; keep only the last _MAX_BACKUPS."""
    if not os.path.exists(DB_FILE):
        return
    backup_dir = os.path.join(DATA_FOLDER, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        shutil.copy(DB_FILE, os.path.join(backup_dir, f"library_{ts}.db"))
        # Prune oldest backups beyond the cap
        backups = sorted(
            [f for f in os.listdir(backup_dir) if f.startswith("library_") and f.endswith(".db")]
        )
        for old in backups[:-_MAX_BACKUPS]:
            os.remove(os.path.join(backup_dir, old))
    except Exception as e:
        print(f"⚠️  DB backup failed: {e}")


# ── Bulk interface (used by library_logic.py / CLI) ───────────────────────────

def load_books() -> list[dict]:
    """Return every book as a list of dicts, ordered by timestamp."""
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM books ORDER BY timestamp ASC").fetchall()
    return [_to_dict(r) for r in rows]


def save_books(books: list[dict]):
    """
    Sync the in-memory book list back to SQLite.

    - Books that carry an `id` are upserted (INSERT OR REPLACE preserves the id).
    - Books without an `id` are inserted fresh (autoincrement assigns a new id).
    - Any book id that was in the DB but is no longer in the list is deleted.
    """
    _backup_db()
    with get_conn() as conn:
        existing_ids = {row[0] for row in conn.execute("SELECT id FROM books")}
        incoming_ids = {b["id"] for b in books if b.get("id") is not None}

        # Delete books that were removed from the list
        for removed_id in existing_ids - incoming_ids:
            conn.execute("DELETE FROM books WHERE id = ?", (removed_id,))

        for b in books:
            p = _book_params(b)
            if b.get("id") is not None:
                conn.execute("""
                    INSERT OR REPLACE INTO books
                        (id, title, author, genre, tags, status, rating, blurb,
                         notes, event, timestamp, last_updated)
                    VALUES
                        (:id, :title, :author, :genre, :tags, :status, :rating, :blurb,
                         :notes, :event, :timestamp, :last_updated)
                """, {"id": b["id"], **p})
            else:
                conn.execute("""
                    INSERT INTO books
                        (title, author, genre, tags, status, rating, blurb,
                         notes, event, timestamp, last_updated)
                    VALUES
                        (:title, :author, :genre, :tags, :status, :rating, :blurb,
                         :notes, :event, :timestamp, :last_updated)
                """, p)


# ── Direct CRUD (used by api.py — no load-all overhead) ──────────────────────

def db_add_book(book: dict) -> dict:
    """Insert a single new book. Returns the book dict with its new `id`."""
    p = _book_params(book)
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO books
                (title, author, genre, tags, status, rating, blurb,
                 notes, event, timestamp, last_updated)
            VALUES
                (:title, :author, :genre, :tags, :status, :rating, :blurb,
                 :notes, :event, :timestamp, :last_updated)
        """, p)
        row = conn.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _to_dict(row)


def db_update_book(book_id: int, updates: dict) -> dict | None:
    """
    Apply a partial update to a book by id.
    `updates` may contain any subset of: title, author, genre, tags,
    status, rating, blurb, notes.
    Returns the updated book dict, or None if not found.
    """
    allowed = {"title", "author", "genre", "tags", "status", "rating", "blurb", "notes"}
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if not row:
            return None
        book = _to_dict(row)
        for k, v in updates.items():
            if k in allowed:
                book[k] = v
        book["last_updated"] = datetime.datetime.now().isoformat()
        p = _book_params(book)
        conn.execute("""
            UPDATE books SET
                title=:title, author=:author, genre=:genre, tags=:tags,
                status=:status, rating=:rating, blurb=:blurb, notes=:notes,
                event=:event, timestamp=:timestamp, last_updated=:last_updated
            WHERE id = :id
        """, {"id": book_id, **p})
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return _to_dict(row)


def db_delete_book(book_id: int) -> bool:
    """Delete a book by id. Returns True if a row was removed."""
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cur.rowcount > 0


def db_get_by_id(book_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return _to_dict(row) if row else None


def db_find_by_title(title: str) -> dict | None:
    """Exact title match (case-insensitive), then fuzzy fallback (≥ 0.6)."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM books WHERE title = ? COLLATE NOCASE", (title,)
        ).fetchone()
    if row:
        return _to_dict(row)

    # Fuzzy fallback requires loading all titles
    books = load_books()
    best, best_ratio = None, 0.0
    for b in books:
        ratio = difflib.SequenceMatcher(None, title.lower(), b["title"].lower()).ratio()
        if ratio > best_ratio:
            best, best_ratio = b, ratio
    return best if best_ratio >= 0.6 else None


def db_title_exists(title: str) -> bool:
    """Fast check for an exact title duplicate (case-insensitive)."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM books WHERE title = ? COLLATE NOCASE", (title,)
        ).fetchone()
    return row is not None
