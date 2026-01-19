
import discord

from api.riot_api import riot_api
from services import bot_tasks

class DiscordClient(discord.Client):
    async def setup_hook(self):
        await riot_api.update_fields()
        bot_tasks.start_bot_tasks(self)
        return await super().setup_hook()
    
    async def close(self):
        await riot_api.close()
        await super().close()