
from bot import client
import discord
from discord.ext import tasks
import sqlite3

from dao import account_dao
from api.riot_api import riot_api, status_err
import config
from model import game_embed

@tasks.loop(hours=24)
async def periodic_update():
    await riot_api.update_fields()
    try:
        accounts = account_dao.get_accounts()
        for account in accounts:
            res = await riot_api.get_username(account["puuid"])
            err = status_err(res)
            if not err is None:
                print("Bad status @ tasks.update_account_details riot_api.get_username:", err)
                continue
            data = res.json()
            dict = { config.TRANSLATE_ACCOUNT_DTO[k]: v for k, v in data.items() }
            if any(account[k] != v for k, v in dict.items()):
                try:
                    account_dao.update_account(account["puuid"], dict)
                except sqlite3.Error as e: # might require more precise error deteciton
                    print("Error @ tasks.update_account_details accountDAO.update_account:", e)
    except sqlite3.Error as e:
        print("Error @ tasks.update_account_details accountDAO.get_account:", e)

@tasks.loop(minutes=1)
async def check_game_status():
    try:
        accounts = account_dao.get_accounts()
        for account in accounts:
            data = game_embed.get_current_game_data(account) # assume this only returns None on no game found, not riot api error
            edge = 0
            if account["match_id"] is None and not data is None:
                edge = 1
            if not account["match_id"] is None and data is None:
                data = game_embed.get_past_game_data(account, account["match_id"])
                edge = -1
            if edge != 0:
                game = game_embed.game_factory(data)
                embedmsg = game.render_embed()
                try:
                    servers = account_dao.get_account_servers(account["puuid"])
                    for server in servers:
                        try:
                            # TODO: make dedicated dao methods for these for atomicity
                            if edge == 1:
                                msg = await client.get_guild(int(server["server"])).get_channel(int(server["channel"])).send(embed=embedmsg)
                                account_dao.update_account_match_id(account["puuid"], data["match_id"])
                                account_dao.update_server_message(account["puuid"], server["server"], msg.id)
                            if edge == -1:
                                msg = await client.get_guild(int(server["server"])).get_channel(int(server["channel"])).fetch_message(int(server["message"]))
                                await msg.edit(embed=embedmsg)
                                account_dao.update_account_match_id(account["puuid"], None)
                                if account["elo"] != data["players"][account["puuid"]]["elo"]:
                                    account_dao.update_account_elo(account["puuid"], data["players"][account["puuid"]]["elo"])
                                account_dao.update_server_message(account["puuid"], server["server"], None)
                        except (discord.Forbidden, discord.NotFound, discord.HTTPException) as e:
                            print("Error @ tasks.check_game_status discord:", e)
                            continue
                except sqlite3.Error as e:
                    print("Error @ tasks.check_game_status account_dao.get_account_servers|update_account_match_id:", e) # TODO: not very clear
                    continue
    except sqlite3.Error as e:
        print("Error @ tasks.check_game_status accountDAO.get_account:", e)