# main.py
from library_logic import (
    add_book_with_author,
    display_library,
    delete_book,
    update_book_status,
    search_books,
    edit_book,
    chat_with_library,
    bulk_import,
)


def menu():
    print("\n--- 📚 Book Manager ---")
    print("1. Add Book")
    print("2. View Library")
    print("3. Search Books")
    print("4. Update Status")
    print("5. Edit Book Details")
    print("6. Delete Book")
    print("7. 💬 Chat with Library (Ollama)")
    print("8. 📥 Bulk Import from CSV")
    print("9. Exit")

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
        t = input("Which book title do you want to delete? ").strip()
        delete_book(t)

    elif choice == "7":
        chat_with_library()

    elif choice == "8":
        path = input("CSV filepath [press Enter for 'import.csv']: ").strip() or "import.csv"
        bulk_import(path)

    elif choice == "9":
        print("Goodbye! 📖")
        exit()

    else:
        print("Invalid option — please choose 1-9.")


if __name__ == "__main__":
    while True:
        menu()