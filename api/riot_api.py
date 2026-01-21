
import aiohttp
from aiolimiter import AsyncLimiter
import certifi
import ssl

import config

HEADER = { 'X-Riot-Token': config.API_KEY }

class RiotResponse:
    status: int
    data: None | dict | list
    def __init__(self, status, data):
        self.status = status
        self.data = data

# NOTE: this might not be the best way to initialize api request limits
LIMITER_SHORT = AsyncLimiter(*config.REQUEST_LIMIT_SHORT)
LIMITER_LONG = AsyncLimiter(*config.REQUEST_LIMIT_LONG)

class RiotApi:
    session: None | aiohttp.ClientSession
    queue_id: None | dict[int, str]
    version: None | str
    champion_id: None | dict[int, str]
    thumbnail_url: function

    def __init__(self):
        self.session = None
        self.queue_id = None
        self.version = None
        self.champion_id = None
        self.thumbnail_url = self.get_thumbnail_url()

    async def start(self):
        if not self.session:
            # NOTE: I don't understand how this connection stuff work
            #       https://github.com/aio-libs/aiohttp/issues/5375
            #       https://docs.aiohttp.org/en/stable/client_advanced.html#ssl-control-for-tcp-sockets
            self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl.create_default_context(cafile=certifi.where())))

    async def close(self):
        if self.session:
            await self.session.close()

    # TODO: add status check
    async def get_queue_id(self) -> dict[int, str]:
        url = f'https://static.developer.riotgames.com/docs/lol/queues.json'
        async with self.session.get(url) as res:
            data = await res.json()
        return { d["queueId"]: d["description"].replace(" games", "") for d in data if not d.get("description") is None }

    # TODO: loads entire list when only the first entry is wanted
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

    def get_thumbnail_url(self) -> function:
        return lambda champion_name: f'https://ddragon.leagueoflegends.com/cdn/{self.version}/img/champion/{champion_name}.png'

    # TODO: make this change atomic
    #       inconsistent state can occur if an asynchronous task using these occurs while these are getting changed
    #       however, it does not matter in this case particularly because champion_id and thumbnail_id can use older versions
    #       so only problem is when the game has updated but this has not, in which case, there are bigger problems
    #       solution is to check version everytime check_game_status task is ran and update fields when version changes
    #       this however does increase response time
    async def update_fields(self):
        self.queue_id = await self.get_queue_id()
        self.version = await self.get_version()
        self.champion_id = await self.get_champion_id()
        self.thumbnail_url = self.get_thumbnail_url()

    async def _request(self, url: str) -> RiotResponse:
        async with LIMITER_SHORT:
            async with LIMITER_LONG:
                async with self.session.get(url, headers=HEADER) as res:
                    # TODO: add status 429 check
                    obj = RiotResponse(res.status, await res.json())
        return obj

    async def get_puuid(self, username: str, tag: str) -> RiotResponse:
        url = f'https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{username}/{tag}'
        return await self._request(url)

    async def get_username(self, puuid: str) -> RiotResponse:
        url = f'https://americas.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}'
        return await self._request(url)
        
    async def get_region(self, puuid: str) -> RiotResponse:
        url = f'https://americas.api.riotgames.com/riot/account/v1/region/by-game/lol/by-puuid/{puuid}'
        return await self._request(url)

    async def get_elo(self, region: str, puuid: str) -> RiotResponse:
        url = f'https://{region}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}'
        return await self._request(url)

    async def get_current_game(self, region: str, puuid: str) -> RiotResponse:
        url = f'https://{region}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}'
        return await self._request(url)

    async def get_past_game(self, region: str, match_id: str) -> RiotResponse:
        url = f'https://{config.REGIONS[region]}.api.riotgames.com/lol/match/v5/matches/{region.upper()}_{match_id}'
        return await self._request(url)

riot_api = RiotApi()

def status_err(res: RiotResponse) -> str:
    if 200 <= res.status < 300:
        return None
    elif 400 <= res.status < 500:
        return f'Internal error: {res.status}'
    elif 500 <= res.status < 600:
        return f'Riot api error: {res.status}'
    else:
        return f'Unknown error: {res.status}'
