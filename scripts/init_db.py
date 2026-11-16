"""Create the SQLite database. Usage: python scripts/init_db.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config
from app.db import init_db

if __name__ == "__main__":
    init_db()
    print(f"Database ready at {config.DATABASE_PATH}")
