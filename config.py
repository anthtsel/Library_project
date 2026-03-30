import os

_HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(_HERE, "data")
BOOK_FILE = os.path.join(DATA_FOLDER, "books.json")   # kept for migrate.py reference
DB_FILE = os.path.join(DATA_FOLDER, "library.db")
OLLAMA_MODEL = "gemma3:4b"