
from discord.ext import tasks
import sqlite3

from dao import account_dao
from api import riot_api
import config

@tasks.loop(hours=24)
async def update_account_details():
    try:
        accounts = account_dao.get_accounts()
        for account in accounts:
            res = riot_api.get_username(account["puuid"])
            err = riot_api.status_err(res)
            if not err:
                print(err)
                continue
            data = res.json()
            dict = { config.TRANSLATE_ACCOUNT_DTO[k]: v for k, v in data.items() }
            if any(account[k] != v for k, v in data.items()):
                try:
                    account_dao.update_account(account["puuid"], dict)
                except sqlite3.Error as e: # might require more succinct error deteciton
                    print("Error @ accountDAO.update_account:", e)
    except sqlite3.Error as e:
        print("Error @ accountDAO.get_account:", e)

@tasks.loop(minutes=1)
async def check_game_status():
    try:
        accounts = account_dao.get_accounts()
        for account in accounts:
            servers = account_dao.get_account_servers(account["puuid"])
            # TODO: finish this
    except sqlite3.Error as e:
        print("Error @ accountDAO.get_account:", e)