
import config 
from bot import client, tree
from services import account
from services import tasks
from api import riot_api

@client.event
async def on_ready():
    await riot_api.riot_api.update_fields()
    tasks.periodic_update.start()
    tasks.check_game_status.start()
    for g in client.guilds:
        await tree.sync(guild=g)
    print(f'Logged in as {client.user}')

client.run(config.BOT_TOKEN)
