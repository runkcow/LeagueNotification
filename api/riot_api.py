
import requests

import config

HEADER = { 'X-Riot-Token': config.API_KEY }

# hope this doesn't ever break
def get_queue_id() -> dict:
    data = requests.get(f'https://static.developer.riotgames.com/docs/lol/queues.json').json()
    return { d["queueId"]: d["description"].replace(" games", "") for d in data if d.get("description") != None }

# TODO: loads entire array when only the first entry is wanted
def get_version() -> str:
    res = requests.get(f'https://ddragon.leagueoflegends.com/api/versions.json')
    return res.json()[0]

# TODO: loads excess data, 
def get_champion_id() -> dict:
    data = requests.get(f'https://ddragon.leagueoflegends.com/cdn/{get_version()}/data/en_US/champion.json').json()
    return { int(v["key"]): k for k, v in data["data"].items() }

def get_thumbnail_url(champion_name) -> str:
    return f'https://ddragon.leagueoflegends.com/cdn/{get_version()}/img/champion/{champion_name}.png'

def get_puuid(username: str, tag: str) -> requests.Response:
    return requests.get(f'https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{username}/{tag}', headers=HEADER)

def get_username(puuid: str) -> requests.Response:
    return requests.get(f'https://americas.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}', headers=HEADER)

def get_region(puuid: str) -> requests.Response:
    return requests.get(f'https://americas.api.riotgames.com/riot/account/v1/region/by-game/lol/by-puuid/{puuid}', headers=HEADER)

def get_elo(region: str, puuid: str) -> requests.Response:
    return requests.get(f'https://{region}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}', headers=HEADER)
    
def get_current_game(region: str, puuid: str) -> requests.Response:
    return requests.get(f'https://{region}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}', headers=HEADER)
    
def get_past_game(region: str, match_id: str) -> requests.Response:
    return requests.get(f'https://{config.REGIONS[region]}.api.riotgames.com/lol/match/v5/matches/{region.upper()}_{match_id}', headers=HEADER)

def status_err(res: requests.Response) -> str:
    if 200 <= res.status_code < 300:
        return None
    elif 400 <= res.status_code < 500:
        return f'Internal error {res.status_code}'
    elif 500 <= res.status_code < 600:
        return f'Riot api error {res.status_code}'
    else:
        return f'Unknown error {res.status_code}'