
import sqlite3

class DataAccess:
    def __init__ (self, db_path: str = "data.db"):
        self.conn = sqlite3.connect("db_path")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def player_get (self) -> list:
        self.cursor.execute("SELECT * FROM players")
        return self.cursor.fetchall()

    def player_add (self, name: str, channel: str):
        try:
            self.cursor.execute("INSERT INTO players (name, channel) VALUES (?, ?)", (name, channel))
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise

    def player_update_channel (self, name: str, channel: str):
        try:
            self.cursor.execute("UPDATE players SET channel = ? WHERE name = ?", (channel, name))
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise
        
    def player_remove (self, name: str):
        try:
            self.cursor.execute("DELETE FROM players WHERE name = ?", (name))
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            raise

