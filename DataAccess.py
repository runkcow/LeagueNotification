
import sqlite3
import json

class DataAccess:
    def __init__ (self, db_path: str = "data.db"):
        self.conn = sqlite3.connect("db_path")
        self.cursor = self.conn.cursor()

    def get_accounts (self):
        res = self.cursor.execute("SELECT * FROM users")
        
