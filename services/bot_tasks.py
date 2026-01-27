
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
                except sqlite3.Error as e: # might require more precise error detection
                    print("Error @ bot_tasks.update_account_details accountDAO.update_account:", e)
    except sqlite3.Error as e:
        print("Error @ bot_tasks.update_account_details accountDAO.get_account:", e)

# NOTE: due to api request limitations, only check discrepancies when there is an edge
# TODO: heavily reliant on the fact that riot api services or network doesn't drop
#       otherwise, errors will begin popping up
#       add status and network exception checks, facade the riot api usage in a helper file
@tasks.loop(minutes=1)
async def check_game_status(client: discord.Client):
    try:
        accounts = { account["puuid"] : account for account in account_dao.get_accounts() }
        # get current game
        coro = { account["puuid"] : riot_api.get_current_game(account["region"], account["puuid"]) for account in accounts.values() }
        results = dict(zip(coro.keys(), await asyncio.gather(*coro.values(), return_exceptions=True)))
        info = { 
            puuid : {
                "edge" : 0,
                "match_id": None, 
                "data" : game_embed.adapt_current_game_data(res.data) if 200 <= res.status < 300 else None 
            } 
            for puuid, res in results.items() 
        }
        # edge detection
        for puuid, account in accounts.items():
            err = status_err(results[puuid])
            if results[puuid].status != 404 and not err is None:
                print("Bad status @ bot_tasks.check_game_status riot_api.get_current_game:", err)
            # TODO: change the logic to use last_match_id
            elif account["match_id"] is None and not info[puuid]["data"] is None:
                info[puuid]["edge"] = 1
                info[puuid]["match_id"] = info[puuid]["data"]["match_id"] # i don't think this is useful
            elif not account["match_id"] is None and info[puuid]["data"] is None:
                info[puuid]["edge"] = -1
                info[puuid]["match_id"] = account["match_id"]
        # for players that aren't in game and do not have an edge, check their latest match and see if it differs
        # NOTE: kinda shoehorned this code in, might not have the best implementation
        coro = {
            puuid : riot_api.get_latest_game(account["region"], puuid)
            for puuid, account in accounts.items()
            if info[puuid]["edge"] == 0 and info[puuid]["data"] is None
        }
        results = dict(zip(coro.keys(), await asyncio.gather(*coro.values(), return_exceptions=True)))
        for puuid, res in results.items():
            err = status_err(res)
            if not err is None:
                print("Bad status @ bot_tasks.check_game_status riot_api.get_latest_game:", err)
                continue
            match_id = res.data[0].split("_")[1]
            if accounts[puuid]["last_match_id"] != match_id:
                info[puuid]["edge"] = -1
                info[puuid]["match_id"] = match_id
        # updates data with past game if falling edge is detected
        coro = { 
            puuid : riot_api.get_past_game(account["region"], info[puuid]["match_id"])
            for puuid, account in accounts.items() 
            if info[puuid]["edge"] == -1
        }
        results = dict(zip(coro.keys(), await asyncio.gather(*coro.values(), return_exceptions=True)))
        for puuid, res in results.items():
            info[puuid]["data"] = game_embed.adapt_past_game_data(res.data) 
        # gets teammate data
        coro = { 
            ppuuid : game_embed.get_ranked_info(account["region"], ppuuid if ppuuid[0] != "!" else None) 
            for entry in info.values() 
            if not entry["data"] is None
            for ppuuid in entry["data"]["players"]
        }
        results = dict(zip(coro.keys(), await asyncio.gather(*coro.values(), return_exceptions=True)))
        for entry in info.values():
            if not entry["data"] is None:
                for ppuuid, player in entry["data"]["players"].items():
                    player.update(results[ppuuid])
        for puuid, account in accounts.items():
            if info[puuid]["edge"] == 0:
                continue
            discrepancy = 0 if info[puuid]["edge"] == -1 else info[puuid]["data"]["players"][puuid]["elo"] - account["elo"]
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
                            account_dao.update_account_match_id(puuid, info[puuid]["data"]["match_id"])
                            account_dao.update_server_message(puuid, server["server"], msg.id)
                        if info[puuid]["edge"] == -1:
                            if not server["message"] is None:
                                msg = await client.get_guild(int(server["server"])).get_channel(int(server["channel"])).fetch_message(int(server["message"]))
                                await msg.edit(embed=embedmsg)
                                account_dao.update_account_match_id(puuid, None)
                                if account["elo"] != info[puuid]["data"]["players"][puuid]["elo"]:
                                    account_dao.update_account_elo(puuid, info[puuid]["data"]["players"][puuid]["elo"])
                                account_dao.update_server_message(puuid, server["server"], None)
                            else:
                                msg = await client.get_guild(int(server["server"])).get_channel(int(server["channel"])).send(embed=embedmsg)
                                if account["elo"] != info[puuid]["data"]["players"][puuid]["elo"]:
                                    account_dao.update_account_elo(puuid, info[puuid]["data"]["players"][puuid]["elo"])
                        account_dao.update_account_last_match_id(puuid, info[puuid]["match_id"])
                    except (discord.Forbidden, discord.NotFound, discord.HTTPException) as e:
                        print("Error @ bot_tasks.check_game_status discord:", e)
                        continue
            except sqlite3.Error as e:
                print("Error @ bot_tasks.check_game_status account_dao.get_account_servers|update_account_match_id|update_account_last_match_id:", e) # TODO: not very clear
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
