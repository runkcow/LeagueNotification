
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.db"
def getconn (dbpath: str = DB_PATH):
    conn = sqlite3.connect(dbpath, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
