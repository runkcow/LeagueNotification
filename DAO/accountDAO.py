
import sqlite3
from dbconn import conn, cursor

def get_account (server: str) -> list:
    cursor.execute("SELECT a.*, s.channel FROM accounts AS a JOIN servers AS s ON a.puuid = s.puuid WHERE s.server = ?", (server))
    return cursor.fetchall()

def add_account (server: str, channel: str, puuid: str, username: str, tag: str, elo: int, wins: int, losses: int, region: str):
    try:
        cursor.execute("SELECT 1 FROM accounts WHERE puuid = ?", (puuid, ))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO accounts (puuid, username, tag, elo, wins, losses, region) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (puuid, username, tag, elo, wins, losses, region))
        cursor.execute("INSERT INTO servers (puuid, server, channel) VALUES (?, ?, ?)", (puuid, server, channel))
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise

def update_account_elo (puuid: str, elo: int):
    try:
        cursor.execute("UPDATE accounts SET lp = ? WHERE puuid = ?", (elo, puuid))
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise

MUTABLE = { "username", "tag", "elo", "wins", "losses", "region" }
def update_account (puuid: str, dict: dict):
    try:
        updates = { k: v for k, v in dict.items() if k in MUTABLE }
        if not updates:
            return
        col = ", ".join(f"{k} = ?" for k in updates)
        val = list(updates.values())
        val.append(puuid)
        conn.execute(f"UPDATE accounts SET {col} WHERE puuid = ?", val)
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise

def remove_account (server: str, puuid: str):
    try:
        conn.execute("DELETE FROM servers WHERE puuid = ?", (puuid, ))
        conn.execute("SELECT 1 FROM accounts AS a JOIN servers AS s ON a.puuid = s.puuid WHERE a.puuid = ? AND s.server = ?", (puuid, server))
        if not cursor.fetchone():
            cursor.delete("DELETE FROM accounts WHERE puuid = ?", (puuid, ))
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise

        