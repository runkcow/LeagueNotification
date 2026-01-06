
import config 

from bot import client, tree

import Commands.account

@client.event
async def on_ready():
    for g in client.guilds:
        await tree.sync(guild=g)
    print(f"Logged in as {client.user}")

client.run(config.BOT_TOKEN)
