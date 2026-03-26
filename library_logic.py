import os
import json
import datetime
import csv
import random
import difflib
from collections import Counter
from config import BOOK_FILE, DATA_FOLDER
import shutil

# Optional terminal color support
try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=False)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    # Fallback no-op values to avoid checks everywhere
    class Fore:
        GREEN = ""
        YELLOW = ""
        CYAN = ""
        BLUE = ""
        RED = ""

    class Style:
        RESET_ALL = ""

status_colors = {
    "Completed":    Fore.GREEN,
    "Reading":      Fore.YELLOW,
    "Want to Read": Fore.CYAN,
    "Reread":       Fore.BLUE,
    "DNF":          Fore.RED,
}


def colorize_status(status):
    if not status:
        return ""

    status_text = status.strip() if isinstance(status, str) else str(status)
    status_key = status_text.title() if status_text.lower() != "dnf" else "DNF"
    color = status_colors.get(status_key, "")

    if COLORAMA_AVAILABLE and color:
        return f"{color}{status_text}{Style.RESET_ALL}"
    return status_text


# ── Optional Ollama integration ───────────────────────────────────────────────
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


def load_books():
    """Read the JSON file into a Python list."""
    if not os.path.exists(BOOK_FILE):
        return []
    try:
        with open(BOOK_FILE, "r") as file:
            return json.load(file)
    except json.JSONDecodeError:
        return []

def save_books(book_list):
    """Save a Python list into the JSON file."""
    os.makedirs("data/backups", exist_ok=True)
    if os.path.exists(BOOK_FILE):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"data/backups/books_{ts}.json"
        try:
            shutil.copy(BOOK_FILE, backup_path)
        except Exception as e:
            print(f"⚠️  Backup failed: {e}")
    else:
        print("DEBUG: No existing file to back up (first save)")
    os.makedirs(DATA_FOLDER, exist_ok=True)
    with open(BOOK_FILE, "w") as file:
        json.dump(book_list, file, indent=4)


# ── AI helpers ────────────────────────────────────────────────────────────────

def generate_blurb(title, author, genre=""):
    """Use Ollama (gemma3:4b) to generate a one-sentence blurb for a book."""
    if not OLLAMA_AVAILABLE:
        return ""
    genre_hint = f" in the {genre} genre" if genre and genre.lower() != "n/a" else ""
    prompt = (
        f"Write exactly ONE sentence (max 20 words) that serves as an enticing blurb "
        f"for the book '{title}' by {author}{genre_hint}. "
        f"Respond with the sentence only — no quotes, no labels, no extra text."
    )
    try:
        response = ollama.chat(
            model="gemma3:4b",
            messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"].strip()
    except Exception as e:
        print(f"  ⚠  Ollama blurb generation failed: {e}")
        return ""


def chat_with_library():
    """Interactive 'Chat' mode — ask questions about your collection via Ollama."""
    if not OLLAMA_AVAILABLE:
        print("❌  Ollama library not installed. Run: pip install ollama")
        return

    books = load_books()
    if not books:
        print("Your library is empty — nothing to chat about yet!")
        return

    summary_lines = []
    for b in books:
        tags = ", ".join(b.get("tags", [])) or "none"
        blurb = b.get("blurb", "")
        line = (
            f"- '{b['title']}' by {b['author']} | Genre: {b.get('genre','?')} | "
            f"Status: {colorize_status(b.get('status', '?'))} | Rating: {b.get('rating',0)}/5 | "
            f"Tags: {tags}"
        )
        if blurb:
            line += f" | Blurb: {blurb}"
        summary_lines.append(line)

    library_context = "\n".join(summary_lines)
    system_prompt = (
        "You are a knowledgeable librarian assistant. "
        "Answer questions about the user's personal book collection below. "
        "Be concise, friendly, and specific.\n\n"
        f"LIBRARY:\n{library_context}"
    )

    print("\n📚  Conversational Library Mode  (type 'exit' to quit)\n")
    history = []

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit", "q"):
            print("Leaving chat mode.")
            break
        if not user_input:
            continue

        history.append({"role": "user", "content": user_input})

        try:
            response = ollama.chat(
                model="gemma3:4b",
                messages=[{"role": "system", "content": system_prompt}] + history
            )
            reply = response["message"]["content"].strip()
            print(f"\nLibrarian: {reply}\n")
            history.append({"role": "assistant", "content": reply})
        except Exception as e:
            print(f"❌  Ollama error: {e}")
            break


# ── Core CRUD ─────────────────────────────────────────────────────────────────

def add_book_with_author(title, author, event="manual", genre="n/a", tags_string="n/a"):
    books = load_books()

    tag_list = [t.strip().lower() for t in tags_string.split(",") if t.strip()]

    # Duplicate check
    if any(b["title"].lower() == title.lower() for b in books):
        print(f"Skipping: '{title}' is already in your library.")
        return

    # Optional AI blurb
    blurb = ""
    if OLLAMA_AVAILABLE:
        print("  🤖  Generating blurb via Ollama…", end=" ", flush=True)
        blurb = generate_blurb(title, author, genre)
        print("done." if blurb else "skipped.")

    new_book = {
        "title": title,
        "author": author,
        "genre": genre.title(),
        "tags": tag_list,
        "status": "Want to Read",
        "rating": 0,
        "blurb": blurb,
        "event": event,
        "timestamp": datetime.datetime.now().isoformat(),
    }

    books.append(new_book)
    save_books(books)
    print(f"✅  Added: '{title}' by {author}  [{len(tag_list)} tag(s)]")
    if blurb:
        print(f"   📝  {blurb}")


def display_library():
    books = load_books()
    if not books:
        print("Library is empty.")
        return

    # Column widths — tuned for 209-column terminal
    W_TITLE  = 28
    W_AUTHOR = 22
    W_GENRE  = 18
    W_STATUS = 13
    W_RATING = 5
    W_TAGS   = 30
    W_ADDED  = 10
    W_BLURB  = 60

    header = (
        f"{'TITLE':<{W_TITLE}} | "
        f"{'AUTHOR':<{W_AUTHOR}} | "
        f"{'GENRE':<{W_GENRE}} | "
        f"{'STATUS':<{W_STATUS}} | "
        f"{'RATING':<{W_RATING}} | "
        f"{'TAGS':<{W_TAGS}} | "
        f"{'ADDED':<{W_ADDED}} | "
        f"BLURB"
    )
    print(f"\n{header}")
    print("-" * 209)

    for b in books:
        title  = b.get("title",  "Unknown")[:W_TITLE]
        author = b.get("author", "Unknown")[:W_AUTHOR]
        genre  = b.get("genre",  "N/A")[:W_GENRE]
        status_plain = b.get("status", "Unknown")[:W_STATUS]
        status = colorize_status(status_plain)
        blurb  = b.get("blurb",  "")[:W_BLURB]

        # Plain unicode stars — no emoji so padding works correctly
        rating_num = int(b.get("rating", 0))
        rating_str = "★" * rating_num + "☆" * (5 - rating_num)

        tags_raw = ", ".join(b.get("tags", []))[:W_TAGS]

        full_ts   = b.get("timestamp", "")
        date_only = full_ts[:10] if full_ts else "N/A"

        print(
            f"{title:<{W_TITLE}} | "
            f"{author:<{W_AUTHOR}} | "
            f"{genre:<{W_GENRE}} | "
            f"{status:<{W_STATUS}} | "
            f"{rating_str:<{W_RATING}} | "
            f"{tags_raw:<{W_TAGS}} | "
            f"{date_only:<{W_ADDED}} | "
            f"{blurb}"
        )


def delete_book(title_to_remove):
    books = load_books()
    updated = [b for b in books if b["title"].lower() != title_to_remove.lower()]
    if len(updated) < len(books):
        save_books(updated)
        print(f"✅  Deleted: '{title_to_remove}'")
    else:
        print(f"❌  Could not find '{title_to_remove}'")


def update_book_status(title, new_status, rating=None):
    books = load_books()
    found = False
    
    # Exact match first (fast path)
    for b in books:
        if b["title"].lower() == title.lower():
            b["status"] = "DNF" if new_status == "dnf" else new_status.title()
            if rating is not None:
                b["rating"] = rating
            b["last_updated"] = datetime.datetime.now().isoformat()
            found = True
            break
        
    if not found:
        # Fuzzy match on title or author
        candidates = []
        for b in books:
            title_ratio = difflib.SequenceMatcher(None, title.lower(), b["title"].lower()).ratio()
            author_ratio = difflib.SequenceMatcher(None, title.lower(), b["author"].lower()).ratio()
            max_ratio = max(title_ratio, author_ratio)
            if max_ratio > 0.6:  # Tunable cutoff (0.6 = 60% similarity)
                candidates.append((b, max_ratio))
    
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)  # Best match first
            best_book, best_ratio = candidates[0]

            if best_ratio > 0.8 or len(candidates) == 1:
                # Auto-update if confident or only one match
                b = best_book
                b["status"] = "DNF" if new_status == "dnf" else new_status.title()
                if rating is not None:
                    b["rating"] = rating
                b["last_updated"] = datetime.datetime.now().isoformat()
                save_books(books)
                print(f"✅  Updated '{b['title']}' (fuzzy match for '{title}')!")
                return
            
            # Multiple close matches — prompt user
            print(f"\nMultiple close matches for '{title}':")
            for i, (b, ratio) in enumerate(candidates[:5]):  # Show top 5
                print(f"  {i+1}. '{b['title']}' by {b['author']} (similarity: {ratio:.1f})")
            try:
                choice = int(input("Choose one (1-5) or 0 to cancel: ").strip())
                if 1 <= choice <= len(candidates):
                    b = candidates[choice-1][0]
                    b["status"] = "DNF" if new_status == "dnf" else new_status.title()
                    if rating is not None:
                        b["rating"] = rating
                    b["last_updated"] = datetime.datetime.now().isoformat()
                    save_books(books)
                    print(f"✅  Updated '{b['title']}'!")
                    return
            except ValueError:
                pass
            print("❌  Update cancelled.")
        else:
            print(f"❌  Could not find '{title}' (even with fuzzy search)")

def search_books(query):
    books = load_books()
    q = query.lower()

    results = [
        b for b in books
        if q in b["title"].lower()
        or q in b["author"].lower()
        or q in b["status"].lower()
        or q in b.get("genre", "").lower()
        or any(q in tag for tag in b.get("tags", []))
    ]
    results.sort(key=lambda x: x["title"].lower())

    if results:
        print(f"\n--- Found {len(results)} match(es) for '{query}' ---")
        print(f"{'TITLE':<25} | {'AUTHOR':<20} | {'GENRE':<15} | {'STATUS'}")
        print("-" * 75)
        for b in results:
            colored_status = colorize_status(b.get('status', 'Unknown'))
            print(
                f"{b['title']:<25} | {b['author']:<20} | "
                f"{b.get('genre','?'):<15} | {colored_status}"
            )
    else:
        print(f"\nNo books found matching '{query}'.")

#── Pick Random Book ────────────────────────────────────────────────

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
    
#── Edit Book Details ───────────────────────────────────────────────

def edit_book(original_title):
    books = load_books()
    found = False
    for b in books:
        if b["title"].lower() == original_title.lower():
            print(f"\n--- Editing '{b['title']}' ---")
            print("(Leave blank to keep current value)")

            new_t = input(f"New Title [{b['title']}]: ")
            if new_t:
                b["title"] = new_t

            new_a = input(f"New Author [{b['author']}]: ")
            if new_a:
                b["author"] = new_a

            new_g = input(f"New Genre [{b.get('genre','None')}]: ")
            if new_g:
                b["genre"] = new_g.title()

            current_tags = ", ".join(b.get("tags", []))
            new_tags = input(f"New Tags [{current_tags}]: ")
            if new_tags:
                b["tags"] = [t.strip().lower() for t in new_tags.split(",")]

            if OLLAMA_AVAILABLE:
                regen = input("Regenerate AI blurb? (y/N): ").strip().lower()
                if regen == "y":
                    print("  🤖  Generating blurb…", end=" ", flush=True)
                    b["blurb"] = generate_blurb(
                        b["title"], b["author"], b.get("genre", "")
                    )
                    print("done.")

            found = True
            break

    if found:
        save_books(books)
        print("✅  Book details updated successfully.")
    else:
        print(f"❌  Could not find '{original_title}'.")
        

def bulk_import(filepath="import.csv"):
    """Import books from a CSV file."""
    if not os.path.exists(filepath):
        print(f"❌  File '{filepath}' not found.")
        print(f"    Create a CSV with columns: title, author, genre, status, tags, rating")
        return

    books = load_books()
    added = 0
    skipped = 0

    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title  = row.get("title",  "").strip()
            author = row.get("author", "").strip()

            if not title or not author:
                print(f"  ⚠  Skipping row — missing title or author: {row}")
                skipped += 1
                continue

            if any(b["title"].lower() == title.lower() for b in books):
                print(f"  ⚠  Skipping duplicate: '{title}'")
                skipped += 1
                continue

            tags_raw = row.get("tags", "")
            tag_list = [t.strip().lower() for t in tags_raw.split(",") if t.strip()]
            genre    = row.get("genre",  "n/a").strip() or "n/a"
            status   = row.get("status", "Want to Read").strip() or "Want to Read"

            try:
                rating = int(row.get("rating", 0))
                rating = rating if 1 <= rating <= 5 else 0
            except ValueError:
                rating = 0

            new_book = {
                "title":     title,
                "author":    author,
                "genre":     genre.title(),
                "tags":      tag_list,
                "status":    status,
                "rating":    rating,
                "blurb":     "",
                "event":     "csv_import",
                "timestamp": datetime.datetime.now().isoformat(),
            }
            books.append(new_book)
            added += 1
            print(f"  ✅  Added: '{title}' by {author}")

    save_books(books)
    print(f"\n📚  Import complete — {added} added, {skipped} skipped.")
    
def reading_stats():
    books = load_books()
    completed = [b for b in books if b["status"] in ("Completed", "Reread")]
    authors   = Counter(b["author"] for b in completed)
    genres    = Counter(b.get("genre", "N/A") for b in completed)
    print(f"Total read:       {len(completed)}")
    print(f"Top author:       {authors.most_common(1)[0]}")
    print(f"Favourite genre:  {genres.most_common(1)[0]}")