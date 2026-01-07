
import requests
import config

HEADER = { 'X-Riot-Token': config.API_KEY }

def get_puuid (username: str, tag: str) -> requests.Response:
    res = requests.get(f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{username}/{tag}", headers=HEADER)
    return res

def get_username (puuid: str) -> requests.Response:
    res = requests.get(f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}", headers=HEADER)
    return res

def get_region (puuid: str) -> requests.Response:
    res = requests.get(f"https://americas.api.riotgames.com/riot/account/v1/region/by-game/lol/by-puuid/{puuid}", headers=HEADER)
    return res

def get_elo (region: str, puuid: str) -> requests.Response:
    res = requests.get(f"https://{config.REGIONS[region.upper()]}/lol/league/v4/entries/by-puuid/{puuid}")
    return res

def status_default (res: requests.Response) -> str:
    if 200 <= res.status_code < 300:
        return
    elif 400 <= res.status_code < 500:
        return "Internal error"
    elif 500 <= res.status_code < 600:
        return "Riot api error"
    else:
        return "Unknown error"