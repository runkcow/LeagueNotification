
from abc import ABC, abstractmethod
import discord

import config
from api import riot_api
from api import api_adapter
import helper

QUEUE_ID = riot_api.get_queue_id()
CHAMPION_ID = riot_api.get_champion_id()

def get_ranked_info(region: str, puuid: str) -> dict:
    res = riot_api.get_elo(region, puuid)
    err = riot_api.status_err(res)
    if not err:
        print("Bad status @ riot_api.get_elo:", err)
        return {}
    return api_adapter.convert_ranked_data(next((d for d in res.json() if d["queueType"] == "RANKED_SOLO_5x5"), None))

def current_game_data(account: dict) -> dict:
    res = riot_api.get_current_game(account["region"], account["puuid"])
    err = riot_api.status_err(res)
    if not err:
        print("Bad status @ riot_api.get_current_game:", err)
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
        } for player in data["participants"] },
    }

def past_game_data(account: dict, matchid: str) -> dict:
    res = riot_api.get_past_game(account["region"], matchid)
    err = riot_api.status_err(res)
    if not err:
        print("Bad status @ riot_api.get_past_game:", err)
        return None
    data = res.json()    
    return {
        "puuid": account["puuid"],
        "username": account["username"],
        "tag": account["tag"],
        "region": account["region"],
        "matchid": data["metadata"]["matchId"],
        "queueid": data["info"]["queueId"],
        "start_time": data["info"]["gameStartTimestamp"] // 1000,
        "end_time": data["info"]["gameEndTimestamp"] // 1000,
        "players": { player["puuid"]: { 
            "champion": player["championId"],
            "assists": player["assists"],
            "deaths": player["deaths"],
            "kills": player["kills"],
            "damage_to_champions": player["totalDamageDealtToChampions"],
            "win": player["win"],
            **get_ranked_info(account["region"], player["puuid"]),
        } for player in data["info"]["participants"] },
        "remake": data["info"]["participants"][0]["gameEndedInEarlySurrender"], # NOTE: unsure if this is correct
    }

def game_factory(game_data: dict) -> Game:
    if game_data["end_time"] == None:
        return OngoingGame(game_data)
    elif game_data["remake"]:
        return RemakeGame(game_data)
    elif game_data["players"][game_data["puuid"]]["win"]:
        return WonGame(game_data)
    else:
        return LostGame(game_data)

class Game(ABC):
    def __init__(self, data: dict):
        self.data = data

    @abstractmethod
    def render_embed(self) -> discord.Embed:
        pass

def _description_builder(finished: bool, data: dict) -> str:
    # setup data
    CONST_STRLEN = {
        "champion": 1,
        "kda": 1,
        "rank": 7,
        "winrate": 2,
        "wins": 1,
        "losses": 1,        
    }
    strlen = {
        "champion": 0,
        "kda": 0,
        "rank": 0,
        "winrate": 0,
        "wins": 0,
        "losses": 0,
    }
    champion = {}
    kda = {}
    rank = {}
    winrate = {}
    for puuid, player in data["players"].items():
        champion[puuid] = f'{"*" if data["puuid"] == puuid else ""}{CHAMPION_ID[player["champion"]]}'
        if strlen["champion"] < len(champion[puuid]):
            strlen["champion"] = len(champion[puuid])
        if finished:
            kda[puuid] = f'{player["kills"]}/{player["deaths"]}/{player["assists"]}'
            if strlen["kda"] < len(kda[puuid]):
                strlen["kda"] = len(kda[puuid])
        rank[puuid] = helper.display_elo_short(player["elo"])
        winrate[puuid] = round(100 * player["wins"] / (player["wins"] + player["losses"]))
        if strlen["winrate"] < len(f'{winrate[puuid]}%'):
            strlen["winrate"] = len(f'{winrate[puuid]}%')
        if strlen["wins"] < len(str(player["wins"])):
            strlen["wins"] = len(str(player["wins"]))
        if strlen["losses"] < len(str(player["losses"])):
            strlen["losses"] = len(str(player["losses"]))

    # truncate champion if text wrap (on pc) happens
    total_len = sum(v + strlen[k] for k, v in CONST_STRLEN.items())
    if total_len > config.PC_TEXT_WRAP:
        strlen["champion"] -= total_len - config.PC_TEXT_WRAP

    # initial description
    description = [ f'{data["username"]}#{data["tag"]}' ]
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
    description.append(f'```')
    # TODO: finish this
    
    description.append(f'```')

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
        # TODO: complete this
        description = ""
        return discord.Embed(
            title=self.get_title(),
            description=description,
            colour=self.get_colour()
        )

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
