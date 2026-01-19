
import aiohttp
import asyncio
import signal

import config

HEADER = { 'X-Riot-Token': config.API_KEY }

class RiotResponse:
    status: int
    data: dict | list | None
    def __init__(self, status, data):
        self.status = status
        self.data = data

class RiotApi:
    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.queue_id = None
        self.version = None
        self.champion_id = None
        self.thumbnail_url = self.get_thumbnail_url()

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        self.queue_id = await self.get_queue_id()
        self.version = await self.get_version()
        self.champion_id = await self.get_champion_id()
        self.thumbnail_url = await self.get_thumbnail_url()

    async def close(self):
        if self.session:
            await self.session.close()

    # TODO: rebuild api for asynchronous calls, synchronous calls slowing down bot to the point of unresponsiveness
    #       add status check
    async def get_queue_id(self) -> dict[int, str]:
        url = f'https://static.developer.riotgames.com/docs/lol/queues.json'
        async with self.session.get(url) as res:
            data = await res.json()
        return { d["queueId"]: d["description"].replace(" games", "") for d in data if not d.get("description") is None }

    # TODO: loads entire array when only the first entry is wanted
    #       add status check
    async def get_version(self) -> str:
        url = f'https://ddragon.leagueoflegends.com/api/versions.json'
        async with self.session.get(url) as res:
            data = await res.json()
        return data[0]

    # TODO: loads excess data
    async def get_champion_id(self) -> dict[int, str]:
        url = f'https://ddragon.leagueoflegends.com/cdn/{self.version}/data/en_US/champion.json'
        async with self.session.get(url) as res:
            data = await res.json()
        return { int(v["key"]): k for k, v in data["data"].items() }

    # TODO: add status check
    def get_thumbnail_url(self) -> function:
        return lambda champion_name: f'https://ddragon.leagueoflegends.com/cdn/{self.version}/img/champion/{champion_name}.png'

    async def update_fields(self):
        self.queue_id = await self.get_queue_id()
        self.version = await self.get_version()
        self.champion_id = await self.get_champion_id()
        self.thumbnail_url = self.get_thumbnail_url()

    async def get_puuid(self, username: str, tag: str) -> RiotResponse:
        url = f'https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{username}/{tag}'
        async with self.session.get(url, headers=HEADER) as res:
            obj = RiotResponse(res.status, await res.json())
        return obj

    async def get_username(self, puuid: str) -> RiotResponse:
        url = f'https://americas.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}'
        async with self.session.get(url, headers=HEADER) as res:
            obj = RiotResponse(res.status, await res.json())
        return obj 

    async def get_region(self, puuid: str) -> RiotResponse:
        url = f'https://americas.api.riotgames.com/riot/account/v1/region/by-game/lol/by-puuid/{puuid}'
        async with self.session.get(url, headers=HEADER) as res:
            obj = RiotResponse(res.status, await res.json())
        return obj

    async def get_elo(self, region: str, puuid: str) -> RiotResponse:
        url = f'https://{region}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}'
        async with self.session.get(url, headers=HEADER) as res:
            obj = RiotResponse(res.status, await res.json())
        return obj

    async def get_current_game(self, region: str, puuid: str) -> RiotResponse:
        url = f'https://{region}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}'
        async with self.session.get(url, headers=HEADER) as res:
            obj = RiotResponse(res.status, await res.json())
        return obj

    async def get_past_game(self, region: str, match_id: str) -> RiotResponse:
        url = f'https://{config.REGIONS[region]}.api.riotgames.com/lol/match/v5/matches/{region.upper()}_{match_id}'
        async with self.session.get(url, headers=HEADER) as res:
            obj = RiotResponse(res.status, await res.json())
        return obj

riot_api = RiotApi()

# NOTE: I have no clue how this code works tbh
loop = asyncio.get_event_loop()

async def shutdown_riot_api():
    await riot_api.close()
    loop.stop()

for s in (signal.SIGINT, signal.SIGTERM):
    loop.add_signal_handler(s, lambda: asyncio.create_task(shutdown_riot_api()))

def status_err(res: RiotResponse) -> str:
    if 200 <= res.status < 300:
        return None
    elif 400 <= res.status < 500:
        return f'Internal error {res.status}: {RiotResponse.data["status"]["message"]}'
    elif 500 <= res.status < 600:
        return f'Riot api error {res.status}: {RiotResponse.data["status"]["message"]}'
    else:
        return f'Unknown error {res.status}: {RiotResponse.data["status"]["message"]}'
