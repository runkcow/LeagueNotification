
import aiohttp
import asyncio

import config

HEADER = { 'X-Riot-Token': config.API_KEY }

class RiotResponse:
    status: int
    data: dict | list | None
    def __init__(self, status, data):
        self.status = status
        self.data = data

# TODO: rebuild api for asynchronous calls, synchronous calls slowing down bot to the point of unresponsiveness
#       add status check
async def get_queue_id() -> dict:
    url = f'https://static.developer.riotgames.com/docs/lol/queues.json'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as res:
            data = await res.json()
    return { d["queueId"]: d["description"].replace(" games", "") for d in data if not d.get("description") is None }
    

# TODO: loads entire array when only the first entry is wanted
#       add status check
async def get_version() -> str:
    url = f'https://ddragon.leagueoflegends.com/api/versions.json'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as res:
            data = await res.json()
    return data[0]

# TODO: loads excess data
async def get_champion_id() -> dict:
    url = f'https://ddragon.leagueoflegends.com/cdn/{await get_version()}/data/en_US/champion.json'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as res:
            data = await res.json()
    return { int(v["key"]): k for k, v in data["data"].items() }

# TODO: add status check
async def get_thumbnail_url(champion_name) -> str:
    return f'https://ddragon.leagueoflegends.com/cdn/{await get_version()}/img/champion/{champion_name}.png'

async def get_puuid(username: str, tag: str) -> RiotResponse:
    url = f'https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{username}/{tag}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADER) as res:
            obj = RiotResponse(res.status, await res.json())
    return obj

async def get_username(puuid: str) -> RiotResponse:
    url = f'https://americas.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADER) as res:
            obj = RiotResponse(res.status, await res.json())
    return obj 

async def get_region(puuid: str) -> RiotResponse:
    url = f'https://americas.api.riotgames.com/riot/account/v1/region/by-game/lol/by-puuid/{puuid}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADER) as res:
            obj = RiotResponse(res.status, await res.json())
    return obj

async def _get_elo(session: aiohttp.ClientSession, region: str, puuid: str) -> tuple[str, RiotResponse]:
    url = f'https://{region}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}'
    async with session.get(url, headers=HEADER) as res:
        obj = RiotResponse(res.status, await res.json())
    return (puuid, obj)

async def get_elo(region: str, puuids: list[str]) -> dict[str, None | RiotResponse]:
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*(_get_elo(session, region, puuid) for puuid in puuids), return_exceptions=True)
    return { res[0] : None if isinstance(res, Exception) else res[1] for res in results }

async def _get_current_game(session: aiohttp.ClientSession, region: str, puuid: str) -> tuple[str, RiotResponse]:
    url = f'https://{region}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}'
    async with session.get(url, headers=HEADER) as res:
        obj = RiotResponse(res.status, await res.json())
    return (puuid, obj)
    
async def get_current_game(region: str, puuids: list[str]) -> dict[str, None | RiotResponse]:
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*(_get_current_game(session, region, puuid) for puuid in puuids), return_exceptions=True)
    return { res[0] : None if isinstance(res, Exception) else res[1] for res in results }

async def _get_past_game(session: aiohttp.ClientSession, region: str, match_id: str) -> tuple[str, RiotResponse]:
    url = f'https://{config.REGIONS[region]}.api.riotgames.com/lol/match/v5/matches/{region.upper()}_{match_id}'
    async with session.get(url, headers=HEADER) as res:
        obj = RiotResponse(res.status, await res.json())
    return (match_id, obj)

async def get_past_game(region: str, match_ids: list[str]) -> dict[str, None | RiotResponse]:
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*(_get_past_game(session, region, match_id) for match_id in match_ids), return_exceptions=True)
    return { res[0] : None if isinstance(res, Exception) else res[1] for res in results }

def status_err(res: RiotResponse) -> str:
    if 200 <= res.status < 300:
        return None
    elif 400 <= res.status < 500:
        return f'Internal error {res.status}: {RiotResponse.data["status"]["message"]}'
    elif 500 <= res.status < 600:
        return f'Riot api error {res.status}: {RiotResponse.data["status"]["message"]}'
    else:
        return f'Unknown error {res.status}: {RiotResponse.data["status"]["message"]}'
    