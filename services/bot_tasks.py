
import discord
from discord.ext import tasks
import sqlite3
import asyncio

from dao import account_dao
from api.riot_api import riot_api, status_err
from api import api_adapter
import config
from model import game_embed

@tasks.loop(hours=24)
async def check_league_constants():
    if check_league_constants.current_loop == 0: # skip first run
        return
    await riot_api.update_fields()

async def get_ranked_info(region: str, puuid: str) -> dict:
    if puuid is None:
        return api_adapter.convert_ranked_data() 
    res = await riot_api.get_elo(region, puuid)
    if not res.success:
        return api_adapter.convert_ranked_data()
    return api_adapter.convert_ranked_data(next((d for d in res.data if d["queueType"] == "RANKED_SOLO_5x5"), None))

@tasks.loop(hours=24)
async def check_account_details():
    try:
        accounts = account_dao.get_accounts()
        coro = {
            account["puuid"] : riot_api.get_username(account["puuid"])
            for account in accounts
        }
        results = dict(zip(coro.keys(), await asyncio.gather(*coro.values(), return_exceptions=True)))
        for account in accounts:
            if not results[account["puuid"]].success:
                continue
            if any(account[config.TRANSLATE_ACCOUNT_DTO[k]] != v for k, v in results[account["puuid"]].data.items()):
                try:
                    account_dao.update_account(account["puuid"], dict)
                except sqlite3.Error as e: # might require more precise error detection
                    print("Error @ bot_tasks.update_account_details accountDAO.update_account:", e)

        # for account in accounts:
        #     res = await riot_api.get_username(account["puuid"])
        #     err = status_err(res)
        #     if err is not None:
        #         print("Bad status @ bot_tasks.update_account_details riot_api.get_username:", err)
        #         continue
        #     data = res.data
        #     dict = { config.TRANSLATE_ACCOUNT_DTO[k]: v for k, v in data.items() }
        #     if any(account[k] != v for k, v in dict.items()):
        #         try:
        #             account_dao.update_account(account["puuid"], dict)
        #         except sqlite3.Error as e: # might require more precise error detection
        #             print("Error @ bot_tasks.update_account_details accountDAO.update_account:", e)
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
        coro = { 
            account["puuid"] : riot_api.get_current_game(account["region"], account["puuid"]) 
            for account in accounts.values() 
        }
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
            if not results[puuid].success:
                continue
            if account["match_id"] is None and info[puuid]["data"] is not None:
                info[puuid]["edge"] = 1
                info[puuid]["match_id"] = info[puuid]["data"]["match_id"] # this is not used, only here for book keeping
            elif account["match_id"] is not None and info[puuid]["data"] is None:
                info[puuid]["edge"] = -1
                info[puuid]["match_id"] = account["match_id"]
        
        # for accounts that aren't in game and do not have an edge, check their latest match and see if it differs
        coro = {
            puuid : riot_api.get_latest_game(account["region"], puuid)
            for puuid, account in accounts.items()
            if info[puuid]["edge"] == 0 and info[puuid]["data"] is None
        }
        results = dict(zip(coro.keys(), await asyncio.gather(*coro.values(), return_exceptions=True)))
        for puuid, res in results.items():
            if not res.success:
                continue
            match_id = res.data.split("_")[1]
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
            if not res.success:
                # NOTE: shoehorned in to fix edge case
                #       for some reason, players can get into games that loses existence
                #       these games cannot be accessed and are forbidden, don't know what causes this
                if res.data == "Forbidden":
                    # TODO: also implement a single dao transaction for this
                    account_dao.update_account_match_id(puuid, None)
                    account_dao.update_account_last_match_id(puuid, info[puuid]["match_id"])
                    for server in account_dao.get_account_servers(puuid):
                        account_dao.update_server_message(puuid, server["server"], None)
                # NOTE: not sure if this is the behaviour i want
                #       for some reason, sometimes, it fails to grab the past match
                #       i believe its because it hits it right as the match ends
                #       so the player is not in an active game but their match hasn't been added to past games yet
                #       which is why it returns no data
                #       should be fine to do this since it'll just try again next cycle update 
                info[puuid]["edge"] = 0 
                continue
            info[puuid]["data"] = game_embed.adapt_past_game_data(res.data) 
        
        # gets teammate data
        coro = {
            ppuuid : get_ranked_info(account["region"], ppuuid if ppuuid[0] != "!" else None) 
            for entry in info.values() 
            if entry["data"] is not None
            for ppuuid in entry["data"]["players"]
        }
        results = dict(zip(coro.keys(), await asyncio.gather(*coro.values(), return_exceptions=True)))
        for entry in info.values():
            if entry["data"] is not None:
                for ppuuid, player in entry["data"]["players"].items():
                    player.update(results[ppuuid])
        
        # send embed message
        for puuid, account in accounts.items():
            if info[puuid]["edge"] == 0:
                continue
            if info[puuid]["data"] is None:
                print(f'Strange Error : {puuid} | {info[puuid]} : somehow has an edge while having no game data')
                continue
            # NOTE: this should only happen when latest match is different, no detected edges 
            #       however, it'd look like a falling edge
            if not info[puuid]["data"]["endOfGameResult"]:
                print(f'Strange Error : {puuid} | {info[puuid]} : game abort unexpected')
                account_dao.update_account_last_match_id(puuid, info[puuid]["match_id"])
                continue
            discrepancy = 0 if info[puuid]["edge"] == -1 else info[puuid]["data"]["players"][puuid]["elo"] - account["elo"]
            game = game_embed.game_factory(account, info[puuid]["data"])
            embedmsg = game.render_embed()
            try:
                for server in account_dao.get_account_servers(puuid):
                    try:
                        guild = client.get_guild(int(server["server"]))
                        if not guild: # NOTE: kind of a bandage solution compared to just running bot_tasks after bot has loaded
                            continue
                        if discrepancy != 0:
                            await guild.get_channel(int(server["channel"])).send(embed=game_embed.get_discrepancy_embed(account, info[puuid]["data"]["players"][puuid]["elo"]))
                            account_dao.update_account_elo(puuid, info[puuid]["data"]["players"][puuid]["elo"])
                        # TODO: make dedicated dao methods for these for atomicity
                        if info[puuid]["edge"] == 1:
                            msg = await guild.get_channel(int(server["channel"])).send(embed=embedmsg)
                            account_dao.update_account_match_id(puuid, info[puuid]["data"]["match_id"])
                            account_dao.update_server_message(puuid, server["server"], msg.id)
                        if info[puuid]["edge"] == -1:
                            if server["message"] is not None:
                                msg = await guild.get_channel(int(server["channel"])).fetch_message(int(server["message"]))
                                await msg.edit(embed=embedmsg)
                                account_dao.update_account_match_id(puuid, None)
                                if account["elo"] != info[puuid]["data"]["players"][puuid]["elo"]:
                                    account_dao.update_account_elo(puuid, info[puuid]["data"]["players"][puuid]["elo"])
                                account_dao.update_server_message(puuid, server["server"], None)
                            else:
                                msg = await guild.get_channel(int(server["channel"])).send(embed=embedmsg)
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
    except Exception as e:
        print("Unexpected Error @ bot_tasks.check_game_status:", e)

def start_bot_tasks(client: discord.Client):
    if not check_league_constants.is_running():
        check_league_constants.start()
    if not check_account_details.is_running():
        check_account_details.start()
    if not check_game_status.is_running():
        check_game_status.start(client)
