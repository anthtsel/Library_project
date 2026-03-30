"""
One-time migration: data/books.json → data/library.db

Run once:
    python migrate.py

Safe to re-run — will report how many books are already in the DB and skip
inserting duplicates by title (case-insensitive).
"""

import json
import os
import sys

from config import BOOK_FILE
from db import db_title_exists, init_db, load_books

import sqlite3
from config import DB_FILE
from db import _book_params, get_conn


def migrate():
    if not os.path.exists(BOOK_FILE):
        print(f"❌  {BOOK_FILE} not found — nothing to migrate.")
        sys.exit(1)

    with open(BOOK_FILE, encoding="utf-8") as f:
        books = json.load(f)

    if not books:
        print("books.json is empty — nothing to migrate.")
        sys.exit(0)

    init_db()

    already = len(load_books())
    if already:
        print(f"ℹ️   DB already contains {already} book(s). Skipping duplicates by title.")

    inserted = skipped = 0
    with get_conn() as conn:
        for b in books:
            title = b.get("title", "").strip()
            if not title:
                skipped += 1
                continue
            exists = conn.execute(
                "SELECT 1 FROM books WHERE title = ? COLLATE NOCASE", (title,)
            ).fetchone()
            if exists:
                skipped += 1
                continue
            p = _book_params(b)
            conn.execute("""
                INSERT INTO books
                    (title, author, genre, tags, status, rating, blurb,
                     notes, event, timestamp, last_updated)
                VALUES
                    (:title, :author, :genre, :tags, :status, :rating, :blurb,
                     :notes, :event, :timestamp, :last_updated)
            """, p)
            inserted += 1

    total = len(load_books())
    print(f"✅  Migration complete — {inserted} inserted, {skipped} skipped.")
    print(f"📚  DB now contains {total} book(s) at {DB_FILE}")


if __name__ == "__main__":
    migrate()
