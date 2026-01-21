
import math
from abc import ABC, abstractmethod
import discord

import config
from api.riot_api import riot_api, status_err
from api import api_adapter
import helper

def get_discrepancy_embed(account: dict, correct_elo: int) -> discord.Embed:
    description = [f'{account["username"]}#{account["tag"]}']
    description.append(f'\nREGION: {account["region"]}')
    description.append(f'\n{helper.display_elo(correct_elo)}')
    return discord.Embed(
        title=f'DISCREPANCY DETECTED {correct_elo - account["elo"]} LP',
        description="".join(description),
        colour=7419530
    )

async def get_ranked_info(region: str, puuid: str) -> dict:
    if puuid is None:
        return api_adapter.convert_ranked_data() 
    res = await riot_api.get_elo(region, puuid)
    if res.status == 400: # TODO: I don't think this is correct, study how streamer mode affects the api calls
        return api_adapter.convert_ranked_data()
    err = status_err(res)
    if not err is None:
        print("Bad status @ game_embed._get_ranked_info riot_api.get_elo:", err)
        return {}
    return api_adapter.convert_ranked_data(next((d for d in res.data if d["queueType"] == "RANKED_SOLO_5x5"), None))

def adapt_current_game_data(data: dict):
    return {
        "match_id": data["gameId"],
        "queue_id": data["gameQueueConfigId"],
        "start_time": data["gameStartTime"] // 1000,
        "players": { (player["puuid"] if not player["puuid"] is None else f'!{i}') : { 
            "champion": player["championId"],
            "team": player["teamId"], # playerSubteamId does not exist for spectatorV5
        } for i, player in enumerate(data["participants"]) },
    }

# NOTE: deprecated
# async def get_current_game_data(account: dict) -> dict:
#     res = await riot_api.get_current_game(account["region"], account["puuid"])
#     if res.status == 404:
#         return None
#     err = status_err(res)
#     if not err is None:
#         print("Bad status @ game_embed._get_ranked_info riot_api.get_current_game:", err)
#         return None
#     data = res.data
#     return {
#         "puuid": account["puuid"],
#         "username": account["username"],
#         "tag": account["tag"],
#         "region": account["region"],
#         "match_id": data["gameId"],
#         "queue_id": data["gameQueueConfigId"],
#         "start_time": data["gameStartTime"] // 1000,
#         "players": { (player["puuid"] if not player["puuid"] is None else f'!{i}') : { 
#             "champion": player["championId"],
#             **_get_ranked_info(account["region"], player["puuid"]),
#             "team": player["teamId"], # playerSubteamId does not exist for spectatorV5
#         } for i, player in enumerate(data["participants"]) },
#     }

def adapt_past_game_data(data: dict) -> dict:
    return {
        "match_id": data["metadata"]["matchId"],
        "queue_id": data["info"]["queueId"],
        "start_time": data["info"]["gameStartTimestamp"] // 1000,
        "end_time": data["info"]["gameEndTimestamp"] // 1000,
        "players": { (player["puuid"] if not player["puuid"] is None else f'!{i}') : {
            "champion": player["championId"],
            "assists": player["assists"],
            "deaths": player["deaths"],
            "kills": player["kills"],
            "damage": player["totalDamageDealtToChampions"],
            "win": player["win"],
            "team": player["teamId"],
            "subteam": player["playerSubteamId"]
        } for i, player in enumerate(data["info"]["participants"]) },
        "remake": data["info"]["participants"][0]["gameEndedInEarlySurrender"], # NOTE: check if this works
    }

# NOTE: deprecated
# async def get_past_game_data(account: dict, match_id: str) -> dict:
#     res = await riot_api.get_past_game(account["region"], match_id)
#     err = status_err(res)
#     if not err is None:
#         print("Bad status @ game_embed._get_ranked_info riot_api.get_past_game:", err)
#         return None
#     data = res.data
#     return {
#         "puuid": account["puuid"],
#         "username": account["username"],
#         "tag": account["tag"],
#         "region": account["region"],
#         "old_elo": account["elo"],
#         "match_id": data["metadata"]["matchId"],
#         "queue_id": data["info"]["queueId"],
#         "start_time": data["info"]["gameStartTimestamp"] // 1000,
#         "end_time": data["info"]["gameEndTimestamp"] // 1000,
#         "players": { (player["puuid"] if not player["puuid"] is None else f'!{i}') : {
#             "champion": player["championId"],
#             "assists": player["assists"],
#             "deaths": player["deaths"],
#             "kills": player["kills"],
#             "damage": player["totalDamageDealtToChampions"],
#             "win": player["win"],
#             **_get_ranked_info(account["region"], player["puuid"]),
#             "team": player["teamId"],
#             "subteam": player["playerSubteamId"]
#         } for i, player in enumerate(data["info"]["participants"]) },
#         "remake": data["info"]["participants"][0]["gameEndedInEarlySurrender"], # NOTE: check if this works
#     }

# TODO: Fix player team, remove the subteam logic or something, also duplicate code exists
#       Merge strlen and the other data maybe
def _description_builder(obj: Game) -> str:
    # NOTE: this exists to save work on refactoring all the code
    finished = not isinstance(obj, OngoingGame)
    account = obj.account
    data = obj.data

    # whitespace 
    CONST_STRLEN = {
        "champion" : 1,
        "kda"      : 1,
        "damage"   : 1,
        "tier"     : 0,
        "lp"       : 1,
        "winrate"  : 1,
        "wins"     : 0,
        "losses"   : 0,        
    }
    # base len, caused by column name
    strlen = {
        "champion" : config.TEAM_NAME_LEN, # (RED/BLUE)
        "kda"      : 3,
        "damage"   : 3,
        "tier"     : 0,
        "lp"       : 0,
        "winrate"  : 3,
        "wins"     : 0,
        "losses"   : 0,
    }
    # NOTE: perhaps this should be a dict of puuids pointing towards data but both ways work
    dispdata = {
        "champion" : {}, 
        "kda"      : {},
        "damage"   : {},
        "tier"     : {},
        "lp"       : {},
        "winrate"  : {},
        "wins"     : {},
        "losses"   : {},
    }
    NO_DATA = "No Data"
    for puuid, player in data["players"].items():
        dispdata["champion"][puuid] = f'{"*" if account["puuid"] == puuid else ""}{riot_api.champion_id[player["champion"]]}'
        strlen["champion"] = max(strlen["champion"], len(dispdata["champion"][puuid]))
        if finished:
            dispdata["kda"][puuid] = f'{player["kills"]}/{player["deaths"]}/{player["assists"]}'
            dispdata["damage"][puuid] = f'{math.floor(player["damage"] / 100) / 10:.1f}k'
            strlen["kda"] = max(strlen["kda"], len(dispdata["kda"][puuid]))
            strlen["damage"] = max(strlen["damage"], len(dispdata["damage"][puuid]))
        if player["wins"] + player["losses"] != 0:
            eloparts = helper.get_elo_parts(player["elo"])
            # including whitespace in dispdata is bad but no other way to deal with Unranked players
            dispdata["tier"][puuid] = f'{eloparts[0][0]}{config.RANK_NUMERICAL[eloparts[1]]} ' 
            dispdata["lp"][puuid] = f'{eloparts[2]}LP'
            dispdata["winrate"][puuid] = f'{round(100 * player["wins"] / (player["wins"] + player["losses"]))}%'
            dispdata["wins"][puuid] = f'{player["wins"]}W'
            dispdata["losses"][puuid] = f'{player["losses"]}L'
            strlen["tier"] = max(strlen["tier"], len(dispdata["tier"][puuid]))
            strlen["lp"] = max(strlen["lp"], len(dispdata["lp"][puuid]))
            strlen["winrate"] = max(strlen["winrate"], len(dispdata["winrate"][puuid]))
            strlen["wins"] = max(strlen["wins"], len(dispdata["wins"][puuid]))
            strlen["losses"] = max(strlen["losses"], len(dispdata["losses"][puuid]))
        else:
            dispdata["tier"][puuid] = NO_DATA
            dispdata["lp"][puuid] = ""
            dispdata["winrate"][puuid] = ""
            dispdata["wins"][puuid] = ""
            dispdata["losses"][puuid] = ""

    # team name check
    if not data["players"][account["puuid"]].get("subteam") is None and data["players"][account["puuid"]]["subteam"] != 0: # dupe
        strlen["champion"] = max(strlen["champion"], config.SUB_TEAM_LEN)

    # truncate champion if text wrap (on pc) happens
    total_len = sum(v + strlen[k] for k, v in CONST_STRLEN.items())
    if total_len > config.PC_TEXT_WRAP:
        strlen["champion"] -= total_len - config.PC_TEXT_WRAP

    # initial description
    description = [ f'{account["username"]}#{account["tag"]}' ]
    description.append(f'\nREGION: {account["region"]}')
    if finished:
        description.append(f'\n{helper.second_str_display(data["end_time"] - data["start_time"])}')
    description.append(f'\n<t:{data["start_time"]}:t>')
    if finished:
        description.append(f' - <t:{data["end_time"]}:t>')
        description.append(f'\nKDA: {dispdata["kda"][account["puuid"]]}')
    description.append(f'\n{riot_api.queue_id[data["queue_id"]]}')
    if data["queue_id"] == 420: # NOTE: this number may need to be updated in the future        
        description.append(f'\n{helper.display_elo(data["players"][account["puuid"]]["elo"])}')
    
    # gamedata representation
    teams = {}
    for puuid, player in data["players"].items():
        team = player["subteam"] if not player.get("subteam") is None and player["subteam"] != 0 else player["team"] # dupe
        if teams.get(team) is None:
            teams[team] = []
        playerstr = [f'\n{dispdata["champion"][puuid][:strlen["champion"]]:{strlen["champion"]}}']
        if finished:
            playerstr.append(f' {dispdata["kda"][puuid]:{strlen["kda"]}} {dispdata["damage"][puuid]:>{strlen["damage"]}}')
        if dispdata["tier"][puuid] != NO_DATA:
            playerstr.append(f' {dispdata["tier"][puuid]:{strlen["tier"]}}{dispdata["lp"][puuid]:>{strlen["lp"]}}')
            playerstr.append(f' {dispdata["winrate"][puuid]:>{strlen["winrate"]}}')
            playerstr.append(f' {dispdata["wins"][puuid]:>{strlen["wins"]}}{dispdata["losses"][puuid]:>{strlen["losses"]}}')
        else:
            playerstr.append(f' {NO_DATA}')
        teams[team].append("".join(playerstr))

    description.append(f'```')
    first = True
    for team, players in teams.items():
        if first:
            description.append(f'{config.TEAM_DISPLAY_NAME[team]:{strlen["champion"]}}')
            if finished:
                description.append(f' {"KDA":{strlen["kda"]}} {"DMG":{strlen["damage"]}}')
            description.append(f' {"RANK":{strlen["tier"] + strlen["lp"]}} {"W/R":{strlen["winrate"] + strlen["wins"] + strlen["losses"] + 1}}')
            first = False
        else:
            description.append(f'\n{config.TEAM_DISPLAY_NAME[team]}') # does not add other headers, only team name
        for player in players:
            description.append(player)
    description.append(f'```')
    return "".join(description)

def game_factory(account: dict, data: dict) -> Game:
    if data.get("end_time") is None:
        return OngoingGame(data)
    elif data["remake"]:
        return RemakeGame(data)
    elif data["players"][account["puuid"]]["win"]:
        return WonGame(data)
    else:
        return LostGame(data)

# TODO: separate account data and game data
class Game(ABC):
    account: dict
    data: dict

    def __init__(self, account: dict, data: dict):
        self.account = account
        self.data = data

    @abstractmethod
    def render_embed(self) -> discord.Embed:
        pass

# TODO: move render_embed to class Game, refactors now cause it to share code
class OngoingGame(Game):
    def render_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="MATCH IN SESSION",
            description=_description_builder(self),
            colour=5763719
        )
        embed.set_thumbnail(url=riot_api.get_thumbnail_url(riot_api.champion_id[self.data["players"][self.account["puuid"]]["champion"]]))
        return embed

class FinishedGame(Game, ABC):
    def render_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=self.get_title(),
            description=_description_builder(self),
            colour=self.get_colour()
        )
        embed.set_thumbnail(url=riot_api.get_thumbnail_url(riot_api.champion_id[self.data["players"][self.account["puuid"]]["champion"]]))
        return embed

    @abstractmethod
    def get_title(self) -> str:
        pass

    # TODO: put the colours in config
    @abstractmethod
    def get_colour(self) -> int:
        pass

class WonGame(FinishedGame):
    def get_title(self) -> str:
        if self.data["queue_id"] == 420:
            return f'MATCH WON {str(self.data["players"][self.data["puuid"]]["elo"] - self.data["old_elo"])} LP'
        return f'MATCH WON'

    def get_colour(self) -> int:
        return 3447003

class LostGame(FinishedGame):
    def get_title(self) -> str:
        if self.data["queue_id"] == 420:
            return f'MATCH LOSS {str(self.data["players"][self.data["puuid"]]["elo"] - self.data["old_elo"])} LP'
        return f'MATCH LOSS'

    def get_colour(self) -> int:
        return 15548997
    
class RemakeGame(FinishedGame):
    def get_title(self) -> str:
        return "REMAKE"

    def get_colour(self) -> int:
        return 16776960
