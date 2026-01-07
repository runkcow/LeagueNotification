
from discord.ext import tasks
import sqlite3

import DAO.accountDAO as accountDAO
import API.riotAPI as riotAPI
import config

@tasks.loop(hours=24)
async def updateAccountDetails():
    try:
        accounts = accountDAO.get_account()
        for account in accounts:
            res = riotAPI.get_username(account["puuid"])
            default = riotAPI.status_default(res)
            if not default:
                print(default)
                continue
            data = res.json()
            dict = { config.TRANSLATE_ACCOUNT_DTO[k]: v for k, v in data.items() }
            if any(account[k] != v for k, v in data.items()):
                try:
                    accountDAO.update_account(account["puuid"], dict)
                except sqlite3.Error as e: # might require more succinct error deteciton
                    print("Error @ accountDAO.update_account:", e)
    except sqlite3.Error as e:
        print("Error @ accountDAO.get_account:", e)

@tasks.loop(minutes=1)
async def checkGameStatus():
    try:
        accounts = accountDAO.get_accounts()
        for account in accounts:
            servers = accountDAO.get_account_servers(account["puuid"])
            # TODO: finish this
    except sqlite3.Error as e:
        print("Error @ accountDAO.get_account:", e)