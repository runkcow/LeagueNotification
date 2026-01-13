
import config 
from bot import client, tree
from services import account
from services import tasks

@client.event
async def on_ready():
    tasks.update_account_details.start()
    tasks.check_game_status.start()
    for g in client.guilds:
        await tree.sync(guild=g)
    print(f'Logged in as {client.user}')

client.run(config.BOT_TOKEN)
