
from discord import app_commands
import discord

import config

intents = discord.Intents.default()
intents.guilds = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

GUILD_LIST = [ discord.Object(id=g) for g in config.DEV_SERVERS ]
