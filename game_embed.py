
import math
from abc import ABC, abstractmethod
import discord

import config
from api import riot_api
from api import api_adapter
import helper

# TODO: these could get updated so they should be updated when version changes or refreshed when used
QUEUE_ID = riot_api.get_queue_id()
CHAMPION_ID = riot_api.get_champion_id()

def get_ranked_info(region: str, puuid: str) -> dict:
    res = riot_api.get_elo(region, puuid)
    err = riot_api.status_err(res)
    if not err is None:
        print("Bad status @ game_embed.get_ranked_info riot_api.get_elo:", err)
        return {}
    return api_adapter.convert_ranked_data(next((d for d in res.json() if d["queueType"] == "RANKED_SOLO_5x5"), None))

def get_current_game_data(account: dict) -> dict:
    res = riot_api.get_current_game(account["region"], account["puuid"])
    if res.status_code == 404:
        return None
    err = riot_api.status_err(res)
    if not err is None:
        print("Bad status @ game_embed.get_ranked_info riot_api.get_current_game:", err)
        return None
    data = res.json()
    return {
        "puuid": account["puuid"],
        "username": account["username"],
        "tag": account["tag"],
        "region": account["region"],
        "match_id": data["gameId"],
        "queue_id": data["gameQueueConfigId"],
        "start_time": data["gameStartTime"] // 1000,
        "players": { player["puuid"]: { 
            "champion": player["championId"],
            **get_ranked_info(account["region"], player["puuid"]),
            "team": player["teamId"], # playerSubteamId does not exist for spectatorV5
        } for player in data["participants"] },
    }

def get_past_game_data(account: dict, match_id: str) -> dict:
    res = riot_api.get_past_game(account["region"], match_id)
    err = riot_api.status_err(res)
    if not err is None:
        print("Bad status @ game_embed.get_ranked_info riot_api.get_past_game:", err)
        return None
    data = res.json()    
    return {
        "puuid": account["puuid"],
        "username": account["username"],
        "tag": account["tag"],
        "region": account["region"],
        "old_elo": account["elo"],
        "matchid": data["metadata"]["matchId"],
        "queueid": data["info"]["queueId"],
        "start_time": data["info"]["gameStartTimestamp"] // 1000,
        "end_time": data["info"]["gameEndTimestamp"] // 1000,
        "players": { player["puuid"]: { 
            "champion": player["championId"],
            "assists": player["assists"],
            "deaths": player["deaths"],
            "kills": player["kills"],
            "damage": player["totalDamageDealtToChampions"],
            "win": player["win"],
            **get_ranked_info(account["region"], player["puuid"]),
            "team": player["teamId"],
            "subteam": player["playerSubteamId"]
        } for player in data["info"]["participants"] },
        "remake": data["info"]["participants"][0]["gameEndedInEarlySurrender"], # NOTE: unsure if this is correct
    }

# TODO: Fix inconsistent const strlen and variable strlen
#       Make display string translation more robust
#       Include separator whitespaces in variables
def _description_builder(finished: bool, data: dict) -> str:
    # setup data
    CONST_STRLEN = {
        "champion": 1,
        "kda": 1,
        "damage": 2,
        "rank": 7,
        "winrate": 1,
        "wins": 1,
        "losses": 1,        
    }
    strlen = {
        "champion": config.TEAM_NAME_LEN, # (RED/BLUE)
        "kda": 3,
        "damage": 3,
        "rank": 0,
        "winrate": 3,
        "wins": 0,
        "losses": 0,
    }
    champion = {} # NOTE: maybe combine these into a single dict
    kda = {}
    damage = {}
    rank = {}
    winrate = {}
    for puuid, player in data["players"].items():
        champion[puuid] = f'{"*" if data["puuid"] == puuid else ""}{CHAMPION_ID[player["champion"]]}'
        strlen["champion"] = max(strlen["champion"], len(champion[puuid]))
        if finished:
            kda[puuid] = f'{player["kills"]}/{player["deaths"]}/{player["assists"]}'
            strlen["kda"] = max(strlen["kda"], len(kda[puuid]))
            damage[puuid] = f'{math.floor(player["damage"] / 100) / 10:.1f}'
            strlen["damage"] = max(strlen["damage"], len(damage[puuid]))
        rank[puuid] = helper.display_elo_short(player["elo"])
        winrate[puuid] = round(100 * player["wins"] / (player["wins"] + player["losses"]))

        strlen["winrate"] = max(strlen["winrate"], len(f'{winrate[puuid]}%'))
        strlen["wins"] = max(strlen["wins"], len(str(player["wins"])))
        strlen["losses"] = max(strlen["losses"], len(str(player["losses"])))

    # team name check
    if not data["players"][data["puuid"]]["subteam"] is None or data["players"][data["puuid"]]["subteam"] != 0:
        strlen["champion"] = max(strlen["champion"], config.SUB_TEAM_LEN)

    # truncate champion if text wrap (on pc) happens
    total_len = sum(v + strlen[k] for k, v in CONST_STRLEN.items())
    if total_len > config.PC_TEXT_WRAP:
        strlen["champion"] -= total_len - config.PC_TEXT_WRAP

    # initial description
    description = [ f'{data["username"]}#{data["tag"]} {data["region"]}' ]
    if finished:
        description.append(f'\n{helper.second_str_display(data)}')
    description.append(f'\n<t:{data["start_time"]}:t>')
    if finished:
        description.append(f' - <t:{data["end_time"]}:t>')
        description.append(f'\nKDA: {kda[data["puuid"]]}')
    description.append(f'\n{QUEUE_ID[data["queueid"]]}')
    if data["queueid"] == 420: # NOTE: this number may need to be updated in the future        
        description.append(f'\n{helper.display_elo(data["players"][data["puuid"]])}')
    
    # gamedata representation
    teams = {}
    for puuid, player in data["players"].items():
        team = player["subteam"] if not player["subteam"] is None or player["subteam"] != 0 else player["team"]
        if teams[team] is None:
            teams[team] = []
        str = [f'\n{champion[puuid]:{strlen["champion"]}}']
        if finished:
            str.append(f' {kda[puuid]:{strlen["kda"]}} {damage[puuid]}k')
        if player["wins"] + player["losses"] == 0:
            str.append(f' Unranked')
        else:
            str.append(f' {rank[puuid]:{strlen["rank"]}} {winrate[puuid]:>{strlen["winrate"]}} {player["wins"]}W{player["losses"]}L')
        teams[team].append("".join(str))

    description.append(f'```')
    first = True
    for team, players in teams.items():
        if first:
            description.append(f'{config.TEAM_DISPLAY_NAME[team]:{strlen["champion"]}}')
            if finished:
                description.append(f' {"KDA":{strlen["kda"]}} {"DMG":{strlen["damage"]}}')
            description.append(f' {"RANK":{strlen["rank"]}} {"W/R":{strlen["winrate"]}}')
            first = False
        else:
            description.append(f'\n{config.TEAM_DISPLAY_NAME[team]}') # does not add other headers, only team name
        for player in players:
            description.append(player)
    description.append(f'```')
    return "".join(description)

def game_factory(game_data: dict) -> Game:
    if game_data["end_time"] == None:
        return OngoingGame(game_data)
    elif game_data["remake"]:
        return RemakeGame(game_data)
    elif game_data["players"][game_data["puuid"]]["win"]:
        return WonGame(game_data)
    else:
        return LostGame(game_data)

# TODO: separate account data and game data
class Game(ABC):
    def __init__(self, data: dict):
        self.data = data

    @abstractmethod
    def render_embed(self) -> discord.Embed:
        pass

# pull ranked solo queue data regardless of game mode
# NOTE: this is probably bad so might need fix
class OngoingGame(Game):
    def render_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="MATCH IN SESSION",
            description=_description_builder(False, self.data),
            colour=5763719
        )
        embed.set_thumbnail(url=riot_api.get_thumbnail_url(CHAMPION_ID[self.data["players"][self.data["puuid"]]["champion"]]))
        return embed

class FinishedGame(Game, ABC):
    def render_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f'{self.get_title()} {str(self.data["players"][self.data["puuid"]]["elo"] - self.data["old_elo"])}',
            description=_description_builder(True, self.data),
            colour=self.get_colour()
        )
        embed.set_thumbnail(url=riot_api.get_thumbnail_url(CHAMPION_ID[self.data["players"][self.data["puuid"]]["champion"]]))
        return embed

    @abstractmethod
    def get_title(self) -> str:
        pass

    @abstractmethod
    def get_colour(self) -> int:
        pass

class WonGame(FinishedGame):
    def get_title(self) -> str:
        return "MATCH WON"

    def get_colour(self) -> int:
        return 3447003

class LostGame(FinishedGame):
    def get_title(self) -> str:
        return "MATCH LOSS"

    def get_colour(self) -> int:
        return 15548997
    
class RemakeGame(FinishedGame):
    def get_title(self) -> str:
        return "REMAKE"

    def get_colour(self) -> int:
        return 16776960
