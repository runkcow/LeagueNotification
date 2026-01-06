
from discord import app_commands
import discord

GUILD_LIST = list(map(lambda g: discord.Object(id=g.id), discord.Client.guilds))

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
