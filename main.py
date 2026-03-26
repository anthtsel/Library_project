# main.py
import argparse
import sys
from library_logic import (
    add_book_with_author,
    display_library,
    delete_book,
    update_book_status,
    search_books,
    edit_book,
    chat_with_library,
    bulk_import,
    pick_random_book,
    reading_stats,
)


def menu():
    print("\n--- 📚 Book Manager ---")
    print("1. Add Book")
    print("2. View Library")
    print("3. Search Books")
    print("4. Update Status")
    print("5. Edit Book Details")
    print("6. Pick Random Book")
    print("7. View Reading Stats")
    print("8. 💬 Chat with Library (Ollama)")
    print("9. 📥 Bulk Import from CSV")
    print("10. Delete Book")
    print("11. Exit")

    choice = input("Select an option: ").strip()

    if choice == "1":
        t = input("Title: ").strip()
        a = input("Author: ").strip()
        if not t or not a:
            print("❌  Title and Author are required.")
        else:
            g    = input("Genre        [Enter to skip]: ").strip() or "n/a"
            tags = input("Tags         [Enter to skip]: ").strip() or "n/a"
            s    = input("Status       [Want to Read] : ").strip() or "Want to Read"
            r    = input("Rating 1-5   [Enter to skip]: ").strip()
            rating = int(r) if r.isdigit() and 1 <= int(r) <= 5 else 0
            add_book_with_author(t, a, event="manual", genre=g, tags_string=tags)

    elif choice == "2":
        display_library()

    elif choice == "3":
        q = input("Search (title, author, genre, tag, status): ").strip()
        search_books(q)

    elif choice == "4":
        t = input("Which book title? ").strip()
        options = ["Want to Read", "Reading", "Completed", "Reread", "DNF"]
        print(f"Allowed statuses: {', '.join(options)}")
        s = input("Enter new status: ").strip().lower()

        if s in [opt.lower() for opt in options]:
            user_rating = None
            if s == "completed":
                try:
                    stars = int(input("Stars (1-5): "))
                    if 1 <= stars <= 5:
                        user_rating = stars
                except ValueError:
                    print("Invalid input — keeping previous rating.")
            update_book_status(t, s, user_rating)
        else:
            print(f"❌  '{s}' is not a valid status.")

    elif choice == "5":
        t = input("Enter the EXACT title of the book to edit: ").strip()
        edit_book(t)
        
    elif choice == "6":
        genre_filter = input("Filter by genre? (leave blank for any): ").strip()
        if genre_filter:
            pick_random_book(genre=genre_filter)
        else:
            pick_random_book()
            
    elif choice == "7":
        reading_stats()

    elif choice == "8":
        chat_with_library()

    elif choice == "9":
        path = input("CSV filepath [press Enter for 'import.csv']: ").strip() or "import.csv"
        bulk_import(path)
        
    elif choice == "10":
        t = input("Which book title do you want to delete? ").strip()
        delete_book(t)

    elif choice == "11":
        print("Goodbye! 📖")
        exit()

    else:
        print("Invalid option — please choose 1-11.")

def main():
    # python main.py add "Dune" "Frank Herbert" --genre "Sci-Fi" --tags "space,desert"
    # python main.py search "sanderson"
    # python main.py list
    parser = argparse.ArgumentParser(description="📚 Library Manager")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Add book subcommand
    add_parser = subparsers.add_parser("add", help="Add a new book")
    add_parser.add_argument("title")
    add_parser.add_argument("author")
    add_parser.add_argument("--genre", default="n/a")
    add_parser.add_argument("--tags", default="n/a")
    add_parser.add_argument("--status", default="Want to Read")

    # Search subcommand
    search_parser = subparsers.add_parser("search", help="Search books")
    search_parser.add_argument("query")

    # List subcommand
    list_parser = subparsers.add_parser("list", help="View library")

    args = parser.parse_args()

    if args.command == "add":
        add_book_with_author(args.title, args.author, genre=args.genre, tags_string=args.tags, event="cli", status=args.status)
    elif args.command == "search":
        search_books(args.query)
    elif args.command == "list":
        display_library()
    else:
        parser.print_help()

if __name__ == "__main__":
    # If the user provided arguments (e.g., 'search'), run the CLI logic
    if len(sys.argv) > 1:
        main()
    # Otherwise, enter your interactive loop
    else:
        while True:
            menu()