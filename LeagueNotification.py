from dotenv import load_dotenv
import os

from discord import app_commands
import discord
from discord.ext import tasks

import sqlite3
from DataAccess import DataAccess

load_dotenv(dotenv_path=".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

GUILD_LIST = list(map(lambda g: discord.Object(id=g.id), discord.Client.guilds))

dao = DataAccess()

async def playerautocomplete(interaction: discord.Interaction, current: str) -> list:
    players = dao.player_get()
    matches = [player.name for player in players if current.lower() in player.name.lower()][:25]
    return [app_commands.Choice(name=name, value=name) for name in matches]

@tree.command(name="playeradd", description="Add player to track", guilds=GUILD_LIST)
@app_commands.describe(
    name="Display name of player",
    channel="Output channel of player's games"
)
async def playeradd(interaction: discord.Interaction, name: str, channel: discord.TextChannel):
    try:
        dao.player_add(name, channel.id)
        await interaction.response.send_message("Player successfully added", ephemeral=True)
    except sqlite3.IntegrityError:
        await interaction.response.send_message("Player by that name already exists", ephemeral=True)
    except sqlite3.Error:
        await interaction.response.send_message("Internal error", ephemeral=True)

@tree.command(name="playerchngchnl", description="Change player output channel", guilds=GUILD_LIST)
@app_commands.describe(
    name="Display name of player",
    channel="Output channel of player's games"
)
async def playerchangechannel(interaction: discord.Interaction, name: str, channel: discord.TextChannel):
    try:
        dao.player_update_channel(name, channel.id)
        await interaction.response.send_message("Player channel successfully changed",ephemeral=True)
    except sqlite3.Error:
        await interaction.response.send_message("Internal error", ephemeral=True)
playerchangechannel.autocomplete("name")(playerautocomplete)

@tree.command(name="playerrmv", description="Removes player", guilds=GUILD_LIST)
@app_commands.describe(
    name="Display name of player"
)
async def playerremove(interaction: discord.Interaction, name: str):
    try:
        dao.player_remove(name)
        await interaction.response.send_message("Player successfully removed", ephemeral=True)
    except sqlite3.Error:
        await interaction.response.send_message("Internal error", ephemeral=True)
playerremove.autocomplete("name")(playerautocomplete)

async def accountautocomplete(interaction: discord.Interaction, current: str) -> list:
    # TODO: incomplete
    return []
