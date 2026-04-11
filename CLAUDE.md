# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Optional — for AI blurbs and chat mode
ollama pull gemma4:4b
ollama serve
```

## Running the app

```bash
# Interactive menu
python main.py

# Direct CLI commands
python main.py add "Dune" "Frank Herbert" --genre "Sci-Fi" --tags "space,desert"
python main.py search "sanderson"
python main.py list
```

There are no tests and no linter configured.

## Architecture

All logic lives in three files:

- `config.py` — path constants (`BOOK_FILE`, `DATA_FOLDER`)
- `library_logic.py` — all data operations: CRUD, search, AI blurbs, chat, bulk import, stats
- `main.py` — two entry points in one file: interactive `menu()` loop (no args) and `argparse`-based `main()` (with args)
- `index.html` — standalone web UI, no server; loads/saves `data/books.json` via file picker and exports via download

**Data layer:** `data/books.json` is the single source of truth — a flat JSON array of book objects. Every `save_books()` call first writes a timestamped backup to `data/backups/`.

**AI integration:** `ollama` and `colorama` are both optional — imported inside `try/except` blocks. If unavailable, AI features are silently skipped and terminal output falls back to plain text. The model is hardcoded as `gemma4:4b`.

**Search** uses simple substring matching across title, author, genre, tags, and status. `update_book_status()` also has fuzzy matching via `difflib.SequenceMatcher` with a 0.6 similarity cutoff.

## Book schema

```json
{
    "title": "string",
    "author": "string",
    "genre": "string",
    "tags": ["array", "of", "strings"],
    "status": "Want to Read | Reading | Completed | Reread | DNF",
    "rating": 0,
    "blurb": "string",
    "event": "manual | cli | csv_import",
    "timestamp": "ISO datetime",
    "last_updated": "ISO datetime"
}
```

## Web UI sync

The web UI and CLI share the same `data/books.json` but don't communicate in real time. After editing in the browser, use **Export** to download the updated file and replace `data/books.json` manually.
