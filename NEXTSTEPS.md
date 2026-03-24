# 🗺️ Next Steps — Upgrade Roadmap

A learning roadmap from easy to hard. Each upgrade teaches a concrete Python, AI, or computer science concept that builds directly toward your larger ATLAS project goals.

---

## 🟢 Easy — Core Python Practice

---

### 2. Random book picker
**What you'll learn:** List comprehensions, the `random` module, filtering data.

Add a menu option that picks a random unread book — optionally filtered by genre.

```python
import random

def pick_random_book(genre=None):
    books = load_books()
    pool = [b for b in books if b["status"] == "Want to Read"]
    if genre:
        pool = [b for b in pool if b.get("genre", "").lower() == genre.lower()]
    if not pool:
        print("No books found in that filter.")
        return
    pick = random.choice(pool)
    print(f"\n🎲  Read next: '{pick['title']}' by {pick['author']}")
```

---

### 3. Reading stats dashboard
**What you'll learn:** `datetime` math, aggregation, working with real data.

Add a stats option that shows books read per month, your fastest read (if you track start/end dates), most-read author, and average rating by genre.

```python
from collections import Counter

def reading_stats():
    books = load_books()
    completed = [b for b in books if b["status"] in ("Completed", "Reread")]
    authors   = Counter(b["author"] for b in completed)
    genres    = Counter(b.get("genre", "N/A") for b in completed)
    print(f"Total read:       {len(completed)}")
    print(f"Top author:       {authors.most_common(1)[0]}")
    print(f"Favourite genre:  {genres.most_common(1)[0]}")
```

---

### 4. Automatic backups
**What you'll learn:** File system operations, `shutil`, defensive programming.

Before every `save_books()` call, copy the current JSON to `data/backups/books_TIMESTAMP.json` so you always have a restore point.

```python
import shutil

def save_books(book_list):
    os.makedirs("data/backups", exist_ok=True)
    if os.path.exists(BOOK_FILE):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy(BOOK_FILE, f"data/backups/books_{ts}.json")
    # ... rest of save logic
```

---

### 5. Goodreads CSV import
**What you'll learn:** Working with messy real-world data, CSV parsing, field mapping.

Goodreads lets you export your library from their site. Their column names differ from yours so you'll need to map and clean them — great practice for real data pipelines.

```python
GOODREADS_MAP = {
    "Title":              "title",
    "Author":             "author",
    "Exclusive Shelf":    "status",   # "read" → "Completed", etc.
    "My Rating":          "rating",
    "Bookshelves":        "tags",
}
```

---

---

## 🟡 Medium — Real Python + CS Concepts

### 6. CLI argument support with `argparse`
**What you'll learn:** How real CLI tools are built, `argparse`, making your app scriptable.

Instead of only working through the menu, let commands run directly from the terminal:

```bash
python main.py add "Dune" "Frank Herbert" --genre "Sci-Fi" --tags "space, desert"
python main.py search "sanderson"
python main.py list --status "Want to Read"
```

```python
import argparse

parser = argparse.ArgumentParser(description="Library Manager")
subparsers = parser.add_subparsers(dest="command")

add_parser = subparsers.add_parser("add")
add_parser.add_argument("title")
add_parser.add_argument("author")
add_parser.add_argument("--genre", default="n/a")
add_parser.add_argument("--tags",  default="n/a")
```

This is how tools like `git`, `pip`, and `aws` work under the hood.

---

### 7. Reading goals tracker
**What you'll learn:** Persistent config separate from data, progress tracking, `tqdm` progress bars.

Set a yearly reading goal and track your progress toward it.

```bash
pip install tqdm
```

Store the goal in a separate `config.json`:
```json
{ "yearly_goal": 24, "year": 2026 }
```

Then display a progress bar when you view stats:
```
2026 Reading Goal: [████████░░░░░░░░░░░░] 8/24 (33%)
```

---

### 8. Web scraper for book metadata
**What you'll learn:** HTTP requests, HTML parsing with BeautifulSoup, handling flaky external data.

When adding a book, look it up automatically to fill in genre, page count, and publication year.

```bash
pip install requests beautifulsoup4
```

```python
import requests
from bs4 import BeautifulSoup

def fetch_metadata(title, author):
    # Query Open Library API (free, no key needed)
    url = f"https://openlibrary.org/search.json?title={title}&author={author}&limit=1"
    r = requests.get(url, timeout=5)
    data = r.json()
    if data["docs"]:
        book = data["docs"][0]
        return {
            "genre":      book.get("subject", ["N/A"])[0],
            "year":       book.get("first_publish_year", ""),
            "page_count": book.get("number_of_pages_median", ""),
        }
    return {}
```

---

### 9. SQLite database instead of JSON
**What you'll learn:** Relational databases, SQL basics, why databases beat flat files at scale, Python's built-in `sqlite3`.

This is the single most educational upgrade on the list. You'll learn:
- Why databases have tables, rows, and columns
- How to write `SELECT`, `INSERT`, `UPDATE`, `DELETE` queries
- Why indexing makes search faster
- How your cloud ATLAS project uses PostgreSQL (same concepts, bigger engine)

```python
import sqlite3

conn = sqlite3.connect("data/library.db")
conn.execute("""
    CREATE TABLE IF NOT EXISTS books (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        title     TEXT NOT NULL,
        author    TEXT NOT NULL,
        genre     TEXT DEFAULT 'n/a',
        status    TEXT DEFAULT 'Want to Read',
        rating    INTEGER DEFAULT 0,
        timestamp TEXT
    )
""")
```

---

### 10. Book recommendations via embeddings
**What you'll learn:** Vector embeddings, semantic similarity, ChromaDB — directly applicable to your ATLAS RAG work.

Use `nomic-embed-text` (already in your ATLAS stack) to embed each book's blurb and tags. Store the vectors in ChromaDB. Then find the books most similar to one you loved.

```bash
pip install chromadb
ollama pull nomic-embed-text
```

```python
import chromadb
import ollama

def embed_book(book):
    text = f"{book['title']} {book['author']} {book.get('blurb','')} {' '.join(book.get('tags',[]))}"
    response = ollama.embeddings(model="nomic-embed-text", prompt=text)
    return response["embedding"]

def find_similar(title, top_k=3):
    # Query ChromaDB for nearest neighbours
    ...
```

---

---

## 🟠 Hard — Serious Engineering

### 11. FastAPI REST backend
**What you'll learn:** REST API design, HTTP methods, JSON responses, separating frontend from backend — the architecture used in your cloud ATLAS project.

```bash
pip install fastapi uvicorn
```

```python
from fastapi import FastAPI
app = FastAPI()

@app.get("/books")
def get_books(): ...

@app.post("/books")
def add_book(book: BookModel): ...

@app.patch("/books/{title}")
def update_book(title: str, updates: dict): ...

@app.delete("/books/{title}")
def delete_book(title: str): ...
```

Your `index.html` then calls `fetch("/books")` instead of loading JSON from disk. This is how every real web app works.

---

### 12. Author deep-dive via RAG
**What you'll learn:** Full RAG pipeline, document chunking, retrieval-augmented generation — a miniature version of your ATLAS system applied to something you use daily.

When you finish a book, automatically fetch the author's Wikipedia page, chunk it into paragraphs, embed each chunk, and store in ChromaDB. In chat mode you can then ask "what else has this author written?" and get answers grounded in real retrieved text rather than model hallucination.

```python
def ingest_author(author_name):
    # 1. Fetch Wikipedia page
    # 2. Split into 500-token chunks
    # 3. Embed each chunk with nomic-embed-text
    # 4. Store in ChromaDB with metadata {"author": author_name, "chunk": i}
    ...

def chat_with_rag(question):
    # 1. Embed the question
    # 2. Retrieve top-k relevant chunks from ChromaDB
    # 3. Build prompt: context + question
    # 4. Send to gemma3:4b
    # 5. Return grounded answer
    ...
```

---

### 13. Automated blurb quality scoring
**What you'll learn:** Prompt chaining, LLM self-critique patterns, when and why to validate AI output — core concepts in agentic AI.

After generating a blurb, send it to a second prompt asking the model to rate its own output. If it scores below a threshold, regenerate automatically.

```python
def generate_blurb_with_validation(title, author, genre="", max_attempts=3):
    for attempt in range(max_attempts):
        blurb = generate_blurb(title, author, genre)

        score_prompt = f"""Rate this book blurb from 1-10 for quality and accuracy.
Blurb: "{blurb}"
Respond with ONLY a number between 1 and 10."""

        response = ollama.chat(model="gemma3:4b", messages=[{"role":"user","content":score_prompt}])
        score = int(response["message"]["content"].strip())

        if score >= 7:
            return blurb
        print(f"  ⚠  Blurb scored {score}/10, regenerating (attempt {attempt+1})...")

    return blurb  # return best effort after max attempts
```

---

### 14. Semantic search across reading notes
**What you'll learn:** Full-text semantic search, RAG on personal data, the difference between keyword search and meaning-based search.

Add a `notes` field where you write freeform thoughts on books you've read. Embed the notes and store in ChromaDB. Then search by *meaning*, not just keywords.

```bash
# Finds relevant books even if these exact words don't appear in your notes
python main.py semantic-search "books where the protagonist sacrifices everything"
```

This is the same technique your cloud ATLAS RAG system uses to search documents — applying it to your own reading notes makes it immediately tangible.

---

### 15. Full React frontend
**What you'll learn:** Component architecture, state management, modern web development — the same stack as your cloud ATLAS frontend.

Rebuild `index.html` as a proper React app that talks to your FastAPI backend (upgrade 11). Once you have both working together you have a complete full-stack application using the exact same architecture as a production system.

```
React frontend  →  FastAPI backend  →  SQLite / PostgreSQL
     ↕                   ↕
  index.html          main.py / library_logic.py
  (upgrade 15)        (upgrades 11 + 9)
```

---

## The Learning Arc

Each upgrade is a stepping stone toward what your cloud ATLAS project already does at larger scale:

```
JSON flat file  →  SQLite  →  PostgreSQL (ATLAS already here)
CLI menus       →  argparse  →  FastAPI REST API
Ollama chat     →  embeddings  →  full RAG pipeline
Static HTML     →  fetch() API calls  →  React frontend
```

Every skill compounds directly into your bigger AI engineering goals.

---

## Recommended Starting Order

| Priority | Upgrade | Why |
|----------|---------|-----|
| 1st | Colorama | Instant win, one library, zero risk |
| 2nd | argparse | Teaches a fundamental pattern used everywhere |
| 3rd | SQLite | Single biggest educational return on investment |
| 4th | Embeddings + ChromaDB | Directly extends your ATLAS RAG knowledge |
| 5th | FastAPI | Unlocks the full-stack architecture |
