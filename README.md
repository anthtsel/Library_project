# 📚 Library Manager

A personal book tracking app with a CLI, a web UI, and local AI integration via Ollama. Manage your reading list from the terminal or the browser — everything stays in sync through a single `books.json` file.

---

## Features

- **CLI app** — add, edit, search, delete, and update book status from the terminal
- **Web UI** — bookshelf, card, and list views with live search and filtering
- **AI blurbs** — auto-generated one-sentence descriptions via `gemma3:4b` when adding books
- **Conversational library** — chat mode lets you ask questions about your collection via Ollama
- **CSV bulk import** — import many books at once from a spreadsheet
- **Export** — download your updated `books.json` from the web UI to keep CLI and browser in sync

---

## Project Structure

```
Library_project/
├── config.py           # File path constants (single source of truth)
├── main.py             # CLI menu and user input handling
├── library_logic.py    # All data logic — CRUD, AI, search, display
├── index.html          # Web UI — open directly in any browser, no server needed
├── import.csv          # Optional — drop books here for bulk import
├── requirements.txt    # Python dependencies
└── data/
    └── books.json      # Your library data — created automatically on first use
```

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/anthtsel/Library_project.git
cd Library_project
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. (Optional) Set up Ollama for AI features

Install Ollama from [ollama.com](https://ollama.com), then pull the model:

```bash
ollama pull gemma3:4b
ollama serve
```

The app works fine without Ollama — AI features are silently skipped if it isn't running.

---

## Running the CLI

```bash
source venv/bin/activate   # if not already active
python main.py
```

### Menu options

| Option | Action |
|--------|--------|
| 1 | Add a book (prompts for title, author, genre, tags, status, rating) |
| 2 | View full library as a formatted table |
| 3 | Search by title, author, genre, tag, or status |
| 4 | Update a book's reading status and rating |
| 5 | Edit book details (title, author, genre, tags, regenerate blurb) |
| 6 | Delete a book |
| 7 | Chat with your library via Ollama |
| 8 | Exit |
| 9 | Bulk import from `import.csv` |

---

## Using the Web UI

Open `index.html` directly in your browser — no server needed.

**From WSL terminal:**
```bash
explorer.exe index.html
```

**Or paste this into Windows Explorer:**
```
\\wsl$\Ubuntu\home\atsel\Library_project
```
Then double-click `index.html`.

### Web UI workflow

1. Click **📂 Load books.json** and select `data/books.json`
2. Browse your library in Shelf, Cards, or List view
3. Use the search bar and filters to find books
4. Click any book to open its detail panel
5. Use **＋ Add Book** to add new entries
6. Use **✎ Edit** or **🗑 Delete** on any book
7. Click **⬇ Export** to download the updated `books.json`
8. Replace `data/books.json` with the downloaded file to sync changes back to the CLI

---

## Bulk Import via CSV

Create an `import.csv` file in the project root:

```csv
title,author,genre,status,tags,rating
Dune,Frank Herbert,Sci-Fi,Completed,"space, desert, politics",5
Project Hail Mary,Andy Weir,Sci-Fi,Want to Read,"space, science",0
```

Then from the CLI choose option **9** and press Enter to use the default filename.

---

## Book JSON Schema

```json
{
    "title": "Neuromancer",
    "author": "William Gibson",
    "genre": "Sci-Fi",
    "tags": ["cyberpunk", "ai", "space"],
    "status": "Completed",
    "rating": 5,
    "blurb": "A washed-up hacker is hired for one last job that will change everything.",
    "event": "manual",
    "timestamp": "2026-03-20T22:43:15.202517",
    "last_updated": "2026-03-21T10:00:00.000000"
}
```

**Valid status values:** `Want to Read`, `Reading`, `Completed`, `Reread`, `DNF`

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Data storage | JSON (flat file) |
| AI model | `gemma3:4b` via Ollama |
| Web UI | Vanilla HTML/CSS/JS (no framework, no build step) |
| Environment | Ubuntu / WSL2 |

---

## License

Personal project — feel free to fork and adapt.
