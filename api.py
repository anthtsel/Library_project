"""
FastAPI backend for the Personal Library app.

Run:  uvicorn api:app --reload
Docs: http://localhost:8000/docs
"""

import datetime
from collections import Counter

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal

from config import OLLAMA_MODEL
from db import (
    db_add_book, db_delete_book, db_find_by_title,
    db_title_exists, db_update_book, init_db, load_books,
)
from library_logic import OLLAMA_AVAILABLE, generate_blurb

try:
    import ollama
except ImportError:
    ollama = None

init_db()

app = FastAPI(title="Personal Library API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request / Response models ─────────────────────────────────────────────────


class AddBookRequest(BaseModel):
    title: str
    author: str
    genre: str = "n/a"
    tags: list[str] = []
    status: str = "Want to Read"
    rating: int = Field(default=0, ge=0, le=5)
    notes: str = ""
    generate_ai_blurb: bool = False


class UpdateBookRequest(BaseModel):
    status: str | None = None
    rating: int | None = Field(default=None, ge=0, le=5)
    genre: str | None = None
    tags: list[str] | None = None
    notes: str | None = None
    blurb: str | None = None
    title: str | None = None
    author: str | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


_STATUS_MAP = {
    "want to read": "Want to Read",
    "reading":      "Reading",
    "completed":    "Completed",
    "reread":       "Reread",
    "dnf":          "DNF",
}

def _normalize_status(status: str) -> str:
    return _STATUS_MAP.get(status.strip().lower(), status.strip().title())


# ── Books endpoints ───────────────────────────────────────────────────────────


@app.get("/books")
def get_books(status: str | None = Query(default=None)):
    """Return all books, optionally filtered by status."""
    books = load_books()
    if status:
        books = [b for b in books if b.get("status", "").lower() == status.lower()]
    return books


@app.post("/books", status_code=201)
def add_book(req: AddBookRequest):
    """Add a new book. Returns the created book object."""
    if db_title_exists(req.title):
        raise HTTPException(status_code=409, detail=f"'{req.title}' is already in your library.")

    blurb = ""
    if req.generate_ai_blurb and OLLAMA_AVAILABLE:
        blurb = generate_blurb(req.title, req.author, req.genre, tags=req.tags)

    return db_add_book({
        "title":        req.title,
        "author":       req.author,
        "genre":        req.genre.title(),
        "tags":         [t.strip().lower() for t in req.tags],
        "status":       _normalize_status(req.status),
        "rating":       req.rating,
        "blurb":        blurb,
        "notes":        req.notes,
        "event":        "api",
        "timestamp":    datetime.datetime.now().isoformat(),
        "last_updated": datetime.datetime.now().isoformat(),
    })


@app.get("/books/search")
def search_books(q: str = Query(min_length=1)):
    """Substring search across title, author, genre, tags, and status."""
    books = load_books()
    ql = q.lower()
    results = [
        b for b in books
        if ql in b["title"].lower()
        or ql in b["author"].lower()
        or ql in b.get("status", "").lower()
        or ql in b.get("genre", "").lower()
        or any(ql in tag for tag in b.get("tags", []))
    ]
    return sorted(results, key=lambda x: x["title"].lower())


@app.get("/books/lookup")
async def lookup_book(
    isbn: str | None = Query(default=None),
    title: str | None = Query(default=None),
    author: str | None = Query(default=None),
):
    """
    Look up book metadata. Tries Google Books first, falls back to Open Library.
    Pass either ?isbn=... or ?title=...&author=...
    """
    if not isbn and not title:
        raise HTTPException(status_code=400, detail="Provide isbn or title query param.")

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            result = await _lookup_google_books(client, isbn, title, author)
            if result is None:
                result = await _lookup_open_library(client, isbn, title, author)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Book lookup timed out — external API unreachable.")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Network error: {e}")

    if result is None:
        raise HTTPException(status_code=404, detail="No book found for that query.")
    return result


async def _lookup_google_books(client, isbn, title, author) -> dict | None:
    """Query Google Books API. Returns None on failure or no results."""
    if isbn:
        query = f"isbn:{isbn}"
    else:
        query = f"intitle:{title}"
        if author:
            query += f"+inauthor:{author}"

    resp = await client.get(
        "https://www.googleapis.com/books/v1/volumes",
        params={"q": query, "maxResults": 1},
    )
    if resp.status_code != 200:
        return None

    data = resp.json()
    if not data.get("items"):
        return None

    info = data["items"][0]["volumeInfo"]
    return {
        "title": info.get("title", ""),
        "author": ", ".join(info.get("authors", [])),
        "genre": (info.get("categories") or ["n/a"])[0],
        "description": info.get("description", ""),
        "page_count": info.get("pageCount"),
        "published_date": info.get("publishedDate", ""),
        "cover_url": (info.get("imageLinks") or {}).get("thumbnail", ""),
        "isbn": isbn or "",
        "source": "google_books",
        "average_rating": info.get("averageRating"),
        "ratings_count": info.get("ratingsCount"),
    }


async def _lookup_open_library(client, isbn, title, author) -> dict | None:
    """Query Open Library API. Returns None on failure or no results."""
    if isbn:
        resp = await client.get(f"https://openlibrary.org/isbn/{isbn}.json")
        if resp.status_code != 200:
            return None
        data = resp.json()

        # Fetch the works entry for richer metadata
        works = data.get("works", [])
        description = ""
        subjects = []
        if works:
            work_resp = await client.get(f"https://openlibrary.org{works[0]['key']}.json")
            if work_resp.status_code == 200:
                work = work_resp.json()
                desc = work.get("description", "")
                description = desc if isinstance(desc, str) else desc.get("value", "")
                subjects = work.get("subjects", [])

        authors_raw = data.get("authors", [])
        author_names = []
        for a in authors_raw[:3]:
            try:
                a_resp = await client.get(f"https://openlibrary.org{a['key']}.json")
                if a_resp.status_code == 200:
                    author_names.append(a_resp.json().get("name", ""))
            except (httpx.RequestError, Exception):
                pass

        cover_id = (data.get("covers") or [None])[0]
        cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else ""

        return {
            "title": data.get("title", ""),
            "author": ", ".join(filter(None, author_names)),
            "genre": subjects[0] if subjects else "n/a",
            "description": description,
            "page_count": data.get("number_of_pages"),
            "published_date": str(data.get("publish_date", "")),
            "cover_url": cover_url,
            "isbn": isbn,
            "source": "open_library",
            "average_rating": None,
            "ratings_count": None,
        }

    # Title/author search via Open Library
    params = {"title": title or "", "limit": 1}
    if author:
        params["author"] = author
    resp = await client.get("https://openlibrary.org/search.json", params=params)
    if resp.status_code != 200 or not resp.json().get("docs"):
        return None

    doc = resp.json()["docs"][0]
    cover_id = (doc.get("cover_i") or None)
    cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else ""
    return {
        "title": doc.get("title", ""),
        "author": ", ".join(doc.get("author_name", [])),
        "genre": (doc.get("subject") or ["n/a"])[0],
        "description": "",
        "page_count": doc.get("number_of_pages_median"),
        "published_date": str(doc.get("first_publish_year", "")),
        "cover_url": cover_url,
        "isbn": (doc.get("isbn") or [""])[0],
        "source": "open_library",
        "average_rating": None,
        "ratings_count": None,
    }


@app.get("/books/{title}")
def get_book(title: str):
    """Get a single book by title (exact or fuzzy match)."""
    book = db_find_by_title(title)
    if not book:
        raise HTTPException(status_code=404, detail=f"'{title}' not found.")
    return book


@app.patch("/books/{title}")
def update_book(title: str, req: UpdateBookRequest):
    """Partially update a book. Supports status, rating, genre, tags, notes, title, author."""
    book = db_find_by_title(title)
    if not book:
        raise HTTPException(status_code=404, detail=f"'{title}' not found.")

    if req.rating is not None and not (0 <= req.rating <= 5):
        raise HTTPException(status_code=422, detail="Rating must be 0–5.")

    updates = {}
    if req.status is not None:
        updates["status"] = _normalize_status(req.status)
    if req.rating is not None:
        updates["rating"] = req.rating
    if req.genre is not None:
        updates["genre"] = req.genre.title()
    if req.tags is not None:
        updates["tags"] = [t.strip().lower() for t in req.tags]
    if req.notes is not None:
        updates["notes"] = req.notes
    if req.blurb is not None:
        updates["blurb"] = req.blurb
    if req.title is not None:
        updates["title"] = req.title
    if req.author is not None:
        updates["author"] = req.author

    return db_update_book(book["id"], updates)


@app.delete("/books/{title}", status_code=204)
def delete_book(title: str):
    """Delete a book by title (exact or fuzzy match)."""
    book = db_find_by_title(title)
    if not book:
        raise HTTPException(status_code=404, detail=f"'{title}' not found.")
    db_delete_book(book["id"])


# ── Stats endpoint ────────────────────────────────────────────────────────────


@app.get("/stats")
def get_stats():
    """Return reading stats as structured JSON."""
    books = load_books()
    if not books:
        return {"total": 0}

    now = datetime.datetime.now()
    this_month = now.strftime("%Y-%m")
    this_year = now.strftime("%Y")

    completed = [b for b in books if b.get("status") in ("Completed", "Reread")]
    status_counts = dict(Counter(b.get("status", "Unknown") for b in books))
    authors = Counter(b["author"] for b in completed)
    genres = Counter(b.get("genre", "N/A") for b in completed)
    rated = [b["rating"] for b in completed if b.get("rating", 0) > 0]

    return {
        "total": len(books),
        "by_status": status_counts,
        "added_this_month": sum(1 for b in books if b.get("timestamp", "")[:7] == this_month),
        "added_this_year": sum(1 for b in books if b.get("timestamp", "")[:4] == this_year),
        "average_rating": round(sum(rated) / len(rated), 1) if rated else None,
        "top_author": {"name": authors.most_common(1)[0][0], "count": authors.most_common(1)[0][1]} if authors else None,
        "top_genre": {"name": genres.most_common(1)[0][0], "count": genres.most_common(1)[0][1]} if genres else None,
        "completed_count": len(completed),
    }


# ── AI endpoints ──────────────────────────────────────────────────────────────


@app.post("/blurb/{title}")
def regenerate_blurb(title: str):
    """Regenerate the AI blurb for a book via Ollama."""
    if not OLLAMA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Ollama is not available.")
    book = db_find_by_title(title)
    if not book:
        raise HTTPException(status_code=404, detail=f"'{title}' not found.")
    blurb = generate_blurb(book["title"], book["author"], book.get("genre", ""), tags=book.get("tags"))
    if not blurb:
        raise HTTPException(status_code=502, detail="Ollama returned an empty blurb.")
    db_update_book(book["id"], {"blurb": blurb})
    return {"title": book["title"], "blurb": blurb}


@app.post("/chat")
def chat(req: ChatRequest):
    """
    Single-turn AI librarian chat.
    Pass message + optional history for multi-turn conversation.
    Returns {"reply": "..."}
    """
    if not OLLAMA_AVAILABLE or ollama is None:
        raise HTTPException(status_code=503, detail="Ollama is not available.")

    books = load_books()
    if not books:
        return {"reply": "Your library is empty — add some books first!"}

    status_order = {"Reading": 0, "Reread": 1, "Completed": 2, "Want to Read": 3, "DNF": 4}
    books_sorted = sorted(books, key=lambda b: status_order.get(b.get("status", ""), 5))

    lines = []
    for b in books_sorted:
        tags = ", ".join(b.get("tags", [])) or "none"
        rating_val = b.get("rating", 0)
        rating_str = f"{rating_val}/5" if rating_val else "unrated"
        line = (
            f'"{b["title"]}" by {b["author"]} ({b.get("genre", "?")}) — '
            f'Status: {b.get("status", "?")}, Rating: {rating_str}, Tags: {tags}'
        )
        if b.get("blurb"):
            line += f'. Blurb: {b["blurb"]}'
        lines.append(line)

    system_prompt = (
        "You are a knowledgeable librarian assistant. "
        "Answer questions about the user's personal book collection below. "
        "Be concise, friendly, and specific.\n\n"
        f"LIBRARY:\n" + "\n".join(lines)
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend({"role": m.role, "content": m.content} for m in req.history)
    messages.append({"role": "user", "content": req.message})

    try:
        response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
        return {"reply": response["message"]["content"].strip()}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama error: {e}")
