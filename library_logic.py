import os
import datetime
import csv
import random
import difflib
from collections import Counter
from config import OLLAMA_MODEL
from db import load_books, save_books

_STATUS_MAP = {
    "want to read": "Want to Read",
    "reading":      "Reading",
    "completed":    "Completed",
    "reread":       "Reread",
    "dnf":          "DNF",
}

def _normalize_status(s: str) -> str:
    return _STATUS_MAP.get(s.strip().lower(), s.strip().title())

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



# ── AI helpers ────────────────────────────────────────────────────────────────

def generate_blurb(title, author, genre="", tags=None):
    """Use Ollama to generate a one-sentence blurb for a book."""
    if not OLLAMA_AVAILABLE:
        return ""
    genre_hint = f" in the {genre} genre" if genre and genre.lower() != "n/a" else ""
    tags_hint  = f" Themes include: {', '.join(tags)}." if tags else ""
    prompt = (
        f"Write exactly ONE sentence (max 20 words) that serves as an enticing blurb "
        f"for the book '{title}' by {author}{genre_hint}.{tags_hint} "
        f"Respond with the sentence only — no quotes, no labels, no extra text."
    )
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"].strip()
    except Exception as e:
        print(f"  ⚠  Ollama blurb generation failed: {e}")
        return ""


def regenerate_blurb(title):
    """Find a book by title and regenerate its AI blurb via Ollama."""
    if not OLLAMA_AVAILABLE:
        print("❌  Ollama library not installed. Run: pip install ollama")
        return
    books = load_books()
    for b in books:
        if b["title"].lower() == title.lower():
            print(f"  🤖  Generating blurb for '{b['title']}'…", end=" ", flush=True)
            blurb = generate_blurb(b["title"], b["author"], b.get("genre", ""))
            if blurb:
                b["blurb"] = blurb
                save_books(books)
                print("done.")
                print(f"  📝  {blurb}")
            else:
                print("skipped (Ollama returned empty).")
            return
    print(f"❌  Could not find '{title}'.")


def chat_with_library():
    """Interactive 'Chat' mode — ask questions about your collection via Ollama."""
    if not OLLAMA_AVAILABLE:
        print("❌  Ollama library not installed. Run: pip install ollama")
        return

    books = load_books()
    if not books:
        print("Your library is empty — nothing to chat about yet!")
        return

    status_order = {"Reading": 0, "Reread": 1, "Completed": 2, "Want to Read": 3, "DNF": 4}
    books_sorted = sorted(books, key=lambda b: status_order.get(b.get("status", ""), 5))

    summary_lines = []
    for b in books_sorted:
        tags  = ", ".join(b.get("tags", [])) or "none"
        blurb = b.get("blurb", "")
        rating_val = b.get("rating", 0)
        rating_str = f"{rating_val}/5" if rating_val else "unrated"
        line = (
            f'"{b["title"]}" by {b["author"]} ({b.get("genre", "?")}) — '
            f'Status: {b.get("status", "?")}, Rating: {rating_str}, Tags: {tags}'
        )
        if blurb:
            line += f'. Blurb: {blurb}'
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
            stream = ollama.chat(
                model=OLLAMA_MODEL,
                messages=[{"role": "system", "content": system_prompt}] + history,
                stream=True,
            )
            print("\nLibrarian: ", end="", flush=True)
            reply = ""
            for chunk in stream:
                token = chunk["message"]["content"]
                print(token, end="", flush=True)
                reply += token
            print("\n")
            history.append({"role": "assistant", "content": reply})
        except Exception as e:
            print(f"❌  Ollama error: {e}")
            break


# ── Core CRUD ─────────────────────────────────────────────────────────────────

def add_book_with_author(title, author, event="manual", genre="n/a", tags_string="n/a", status="Want to Read"):
    books = load_books()

    tag_list = [t.strip().lower() for t in tags_string.split(",") if t.strip()]

    # Normalize status
    status = _normalize_status(status)

    # Duplicate check
    if any(b["title"].lower() == title.lower() for b in books):
        print(f"Skipping: '{title}' is already in your library.")
        return

    # Optional AI blurb
    blurb = ""
    if OLLAMA_AVAILABLE:
        print("  🤖  Generating blurb via Ollama…", end=" ", flush=True)
        blurb = generate_blurb(title, author, genre, tags=tag_list)
        print("done." if blurb else "skipped.")

    new_book = {
        "title": title,
        "author": author,
        "genre": genre.title(),
        "tags": tag_list,
        "status": status,
        "rating": 0,
        "blurb": blurb,
        "notes": "",
        "event": event,
        "timestamp": datetime.datetime.now().isoformat(),
    }

    books.append(new_book)
    save_books(books)
    print(f"✅  Added: '{title}' by {author}  [{len(tag_list)} tag(s)]")
    if blurb:
        print(f"   📝  {blurb}")


def display_library(status_filter=None):
    books = load_books()
    if not books:
        print("Library is empty.")
        return
    if status_filter:
        books = [b for b in books if b.get("status", "").lower() == status_filter.lower()]
        if not books:
            print(f"No books with status '{status_filter}'.")
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
            b["status"] = _normalize_status(new_status)
            if rating is not None:
                b["rating"] = rating
            b["last_updated"] = datetime.datetime.now().isoformat()
            save_books(books)
            print(f"✅  Updated '{b['title']}'!")
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
                b["status"] = _normalize_status(new_status)
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
                    b["status"] = _normalize_status(new_status)
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
        if len(results) == 1:
            b = results[0]
            if b.get("blurb"):
                print(f"\n  📝  {b['blurb']}")
            if b.get("notes"):
                print(f"  🗒   Notes: {b['notes']}")
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

            new_notes = input(f"Notes [{b.get('notes', '')}]: ")
            if new_notes:
                b["notes"] = new_notes

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

    with open(filepath, "r", encoding="utf-8") as f:
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
                "notes":     "",
                "event":     "csv_import",
                "timestamp": datetime.datetime.now().isoformat(),
            }
            books.append(new_book)
            added += 1
            print(f"  ✅  Added: '{title}' by {author}")

    save_books(books)
    print(f"\n📚  Import complete — {added} added, {skipped} skipped.")

    if OLLAMA_AVAILABLE and added > 0:
        ans = input(f"Generate AI blurbs for {added} imported book(s)? This may take a while. (y/N): ").strip().lower()
        if ans == "y":
            updated = 0
            for b in books:
                if b.get("event") == "csv_import" and not b.get("blurb"):
                    print(f"  🤖  '{b['title']}'…", end=" ", flush=True)
                    blurb = generate_blurb(b["title"], b["author"], b.get("genre", ""), tags=b.get("tags"))
                    if blurb:
                        b["blurb"] = blurb
                        updated += 1
                        print("done.")
                    else:
                        print("skipped.")
            if updated:
                save_books(books)
                print(f"✅  Generated blurbs for {updated} book(s).")
    
def reading_stats():
    books = load_books()
    if not books:
        print("Library is empty.")
        return

    now       = datetime.datetime.now()
    this_month = now.strftime("%Y-%m")
    this_year  = now.strftime("%Y")

    completed = [b for b in books if b.get("status") in ("Completed", "Reread")]
    authors   = Counter(b["author"] for b in completed)
    genres    = Counter(b.get("genre", "N/A") for b in completed)

    # Count by status
    status_counts = Counter(b.get("status", "Unknown") for b in books)

    # Books added this month / year
    added_month = sum(1 for b in books if b.get("timestamp", "")[:7] == this_month)
    added_year  = sum(1 for b in books if b.get("timestamp", "")[:4] == this_year)

    # Average rating (only books with an explicit rating)
    rated = [b["rating"] for b in completed if b.get("rating", 0) > 0]
    avg_rating = f"{sum(rated)/len(rated):.1f}/5" if rated else "N/A"

    top_author = authors.most_common(1)[0] if authors else ("N/A", 0)
    top_genre  = genres.most_common(1)[0]  if genres  else ("N/A", 0)

    print(f"\n📚  Reading Stats")
    print(f"{'─'*35}")
    print(f"Total in library:    {len(books)}")
    for s in ("Want to Read", "Reading", "Completed", "Reread", "DNF"):
        count = status_counts.get(s, 0)
        if count:
            print(f"  {s:<18} {count}")
    print(f"Added this month:    {added_month}")
    print(f"Added this year:     {added_year}")
    print(f"Average rating:      {avg_rating}")
    print(f"Top author:          {top_author[0]} ({top_author[1]} book{'s' if top_author[1] != 1 else ''})")
    print(f"Favourite genre:     {top_genre[0]} ({top_genre[1]} book{'s' if top_genre[1] != 1 else ''})")