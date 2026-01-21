
import discord
from discord.ext import tasks
import sqlite3
import asyncio

from dao import account_dao
from api.riot_api import riot_api, status_err
import config
from model import game_embed

@tasks.loop(hours=24)
async def check_league_constants():
    if check_league_constants.current_loop == 0: # skip first run
        return
    await riot_api.update_fields()

@tasks.loop(hours=24)
async def check_account_details():
    try:
        accounts = account_dao.get_accounts()
        for account in accounts:
            res = await riot_api.get_username(account["puuid"])
            err = status_err(res)
            if not err is None:
                print("Bad status @ bot_tasks.update_account_details riot_api.get_username:", err)
                continue
            data = res.data
            dict = { config.TRANSLATE_ACCOUNT_DTO[k]: v for k, v in data.items() }
            if any(account[k] != v for k, v in dict.items()):
                try:
                    account_dao.update_account(account["puuid"], dict)
                except sqlite3.Error as e: # might require more precise error deteciton
                    print("Error @ bot_tasks.update_account_details accountDAO.update_account:", e)
    except sqlite3.Error as e:
        print("Error @ bot_tasks.update_account_details accountDAO.get_account:", e)

# TODO: remake this completely lol
@tasks.loop(minutes=1)
async def check_game_status(client: discord.Client):
    try:
        accounts = { account["puuid"] : account for account in account_dao.get_accounts() }
        # get current game
        coro = { account["puuid"] : riot_api.get_current_game(account["region"], account["puuid"]) for account in accounts.values() }
        results = dict(zip(coro.keys(), await asyncio.gather(*coro.values(), return_exceptions=True)))
        info = { puuid : { "edge" : 0, "data" : game_embed.adapt_current_game_data(res.data) if 200 <= res.status < 300 else None } for puuid, res in results.items() }
        # edge detection
        for puuid, account in accounts.items():
            err = status_err(results[puuid])
            if results[puuid].status != 404 and not err is None:
                print("Bad status @ bot_tasks.check_game_status riot_api.get_current_game:", err)
            if account["match_id"] is None and not info[puuid]["data"] is None:
                entry["edge"] = 1
            elif not account["match_id"] is None and info[puuid]["data"] is None:
                entry["edge"] = -1
        # updates data with past game if falling edge is detected
        coro = { 
            account["puuid"] : riot_api.get_past_game(account["region"], account["match_id"]) 
            for puuid, account in accounts.items() 
            if info[puuid]["edge"] == -1 
        }
        results = dict(zip(coro.keys(), await asyncio.gather(*coro.values(), return_exceptions=True)))
        for puuid, res in results.items():
            info[puuid]["data"] = game_embed.adapt_past_game_data(res.data) 
        # gets teammate data
        coro = { 
            ppuuid : game_embed.get_ranked_info(account["region"], ppuuid) 
            for entry in info.values() 
            if not entry["data"] is None
            for ppuuid in entry["data"]["players"]
            if  ppuuid[0] != "!"
        }
        results = dict(zip(coro.keys(), await asyncio.gather(*coro.values(), return_exceptions=True)))
        for entry in info.values():
            if not entry["data"] is None:
                for ppuuid, player in entry["data"]["players"].items():
                    player.update(results[ppuuid])
        # TODO: discrepancy detection doesn't work if there isn't an edge
        for puuid, account in accounts.items():
            discrepancy = 0 if info[puuid]["edge"] == -1 else info[puuid]["data"]["players"][puuid]["elo"] - account["elo"]
            if discrepancy != 0 and info[puuid]["edge"] == 0:
                continue
            game = game_embed.game_factory(account, info[puuid]["data"])
            embedmsg = game.render_embed()
            try:
                servers = account_dao.get_account_servers(puuid)
                for server in servers:
                    try:
                        if discrepancy != 0:
                            await client.get_guild(int(server["server"])).get_channel(int(server["channel"])).send(embed=game_embed.get_discrepancy_embed(account, info[puuid]["data"]["players"][puuid]["elo"]))
                            account_dao.update_account_elo(puuid, info[puuid]["data"]["players"][puuid]["elo"])
                        # TODO: make dedicated dao methods for these for atomicity
                        if info[puuid]["edge"] == 1:
                            msg = await client.get_guild(int(server["server"])).get_channel(int(server["channel"])).send(embed=embedmsg)
                            account_dao.update_account_match_id(account["puuid"], info[puuid]["data"]["match_id"])
                            account_dao.update_server_message(account["puuid"], server["server"], msg.id)
                        if info[puuid]["edge"] == -1:
                            msg = await client.get_guild(int(server["server"])).get_channel(int(server["channel"])).fetch_message(int(server["message"]))
                            await msg.edit(embed=embedmsg)
                            account_dao.update_account_match_id(account["puuid"], None)
                            if account["elo"] != info[puuid]["data"]["players"][account["puuid"]]["elo"]:
                                account_dao.update_account_elo(account["puuid"], info[puuid]["data"]["players"][account["puuid"]]["elo"])
                            account_dao.update_server_message(account["puuid"], server["server"], None)
                    except (discord.Forbidden, discord.NotFound, discord.HTTPException) as e:
                        print("Error @ bot_tasks.check_game_status discord:", e)
                        continue
            except sqlite3.Error as e:
                print("Error @ bot_tasks.check_game_status account_dao.get_account_servers|update_account_match_id:", e) # TODO: not very clear
                continue
    except sqlite3.Error as e:
        print("Error @ bot_tasks.check_game_status accountDAO.get_account:", e)

# NOTE: deprecated
# TODO: implement asyncio gather to asynchronously check all accounts simultaneously
#       consider changing timer to 2 minutes to better fit api request limit
# @tasks.loop(minutes=1)
# async def check_game_status(client: discord.Client): # this is technically model.discord_client.DiscordClient
#     try:
#         accounts = account_dao.get_accounts()
#         for account in accounts:
#             data = await game_embed.get_current_game_data(account) # assume this only returns None on no game found, not riot api error
#             edge = 0
#             if account["match_id"] is None and not data is None:
#                 edge = 1
#             if not account["match_id"] is None and data is None:
#                 data = await game_embed.get_past_game_data(account, account["match_id"])
#                 edge = -1
#             if edge != 0:
#                 game = game_embed.game_factory(data)
#                 embedmsg = game.render_embed()
#                 try:
#                     servers = account_dao.get_account_servers(account["puuid"])
#                     for server in servers:
#                         try:
#                             # TODO: make dedicated dao methods for these for atomicity
#                             if edge == 1:
#                                 msg = await client.get_guild(int(server["server"])).get_channel(int(server["channel"])).send(embed=embedmsg)
#                                 account_dao.update_account_match_id(account["puuid"], data["match_id"])
#                                 account_dao.update_server_message(account["puuid"], server["server"], msg.id)
#                             if edge == -1:
#                                 msg = await client.get_guild(int(server["server"])).get_channel(int(server["channel"])).fetch_message(int(server["message"]))
#                                 await msg.edit(embed=embedmsg)
#                                 account_dao.update_account_match_id(account["puuid"], None)
#                                 if account["elo"] != data["players"][account["puuid"]]["elo"]:
#                                     account_dao.update_account_elo(account["puuid"], data["players"][account["puuid"]]["elo"])
#                                 account_dao.update_server_message(account["puuid"], server["server"], None)
#                         except (discord.Forbidden, discord.NotFound, discord.HTTPException) as e:
#                             print("Error @ bot_tasks.check_game_status discord:", e)
#                             continue
#                 except sqlite3.Error as e:
#                     print("Error @ bot_tasks.check_game_status account_dao.get_account_servers|update_account_match_id:", e) # TODO: not very clear
#                     continue
#     except sqlite3.Error as e:
#         print("Error @ bot_tasks.check_game_status accountDAO.get_account:", e)

def start_bot_tasks(client: discord.Client):
    if not check_league_constants.is_running():
        check_league_constants.start()
    if not check_account_details.is_running():
        check_account_details.start()
    if not check_game_status.is_running():
        check_game_status.start(client)
