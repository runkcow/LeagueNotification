
from dao.dbconn import getconn

def get_account(puuid: str) -> dict:
    with getconn() as conn:
        return conn.execute("SELECT * FROM accounts WHERE puuid = ?", (puuid, )).fetchone()

def get_accounts() -> list:
    with getconn() as conn:
        return conn.execute("SELECT * FROM accounts").fetchall()

def get_account_servers(puuid: str) -> list:
    with getconn() as conn:
        return conn.execute("SELECT a.*, s.server, s.channel, s.message FROM accounts AS a JOIN servers AS s on a.puuid = s.puuid WHERE a.puuid = ?", (puuid, )).fetchall()

def get_server_accounts(server: str) -> list:
    with getconn() as conn:
        return conn.execute("SELECT a.*, s.channel FROM accounts AS a JOIN servers AS s ON a.puuid = s.puuid WHERE server = ?", (server, )).fetchall()

def add_account(server: str, channel: str, puuid: str, username: str, tag: str, elo: int, wins: int, losses: int, region: str):
    with getconn() as conn:
        if not conn.execute("SELECT 1 FROM accounts WHERE puuid = ?", (puuid, )).fetchone():
            conn.execute(
                "INSERT INTO accounts (puuid, username, tag, elo, wins, losses, region) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (puuid, username, tag, elo, wins, losses, region))
        conn.execute("INSERT INTO servers (puuid, server, channel) VALUES (?, ?, ?)", (puuid, server, channel))

def update_account_elo(puuid: str, elo: int):
    with getconn() as conn:
        conn.execute("UPDATE accounts SET elo = ? WHERE puuid = ?", (elo, puuid))

def update_account_channel(server: str, puuid: str, channel: str):
    with getconn() as conn:
        conn.execute("UPDATE servers SET channel = ? WHERE puuid = ? AND server = ?", (channel, puuid, server))

def update_account_match_id(puuid: str, match_id: str):
    with getconn() as conn:
        conn.execute("UPDATE accounts SET match_id = ? WHERE puuid = ?", (match_id, puuid))

MUTABLE = { "username", "tag", "elo", "wins", "losses", "region", "match_id" }
def update_account(puuid: str, dict: dict):
    updates = { k: v for k, v in dict.items() if k in MUTABLE }
    if not updates:
        return
    col = ", ".join(f"{k} = ?" for k in updates)
    val = list(updates.values())
    val.append(puuid)
    with getconn() as conn:
        conn.execute(f"UPDATE accounts SET {col} WHERE puuid = ?", val)

def remove_account(server: str, puuid: str):
    with getconn() as conn:
        conn.execute("DELETE FROM servers WHERE puuid = ?", (puuid, ))
        if not conn.execute("SELECT 1 FROM accounts AS a JOIN servers AS s ON a.puuid = s.puuid WHERE a.puuid = ? AND s.server = ?", (puuid, server)).fetchone():
            conn.execute("DELETE FROM accounts WHERE puuid = ?", (puuid, ))

def update_server_message(puuid: str, server: str, message: str):
    with getconn() as conn:
        conn.execute("UPDATE servers SET message = ? WHERE puuid = ? AND server = ?", (message, puuid, server))
