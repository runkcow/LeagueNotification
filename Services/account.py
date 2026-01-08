
import discord
import sqlite3

import config

from bot import GUILD_LIST, tree
from dao import account_dao
from api import riot_api
from api import api_adapter

async def account_auto_complete(interaction: discord.Interaction, current: str) -> list:
    accounts = account_dao.get_server_accounts(interaction.guild_id)
    matches = [account for account in accounts if current.lower() in f'{account["username"]}#{account["tag"]}'.lower()][:25]
    return [discord.app_commands.Choice(name=f'{account["username"]}#{account["tag"]}', value=account["puuid"]) for account in matches]

@tree.command(name="acountadd", description="Add account to track", guilds=GUILD_LIST)
@discord.app_commands.describe(
    username="Username of account",
    tag="Tag of account",
    channel="Output channel"
)
@discord.app_commands.choices(
    region=[ discord.app_commands.Choice(name=k, value=v) for k, v in config.REGIONS.items() ]
)   
async def account_add(interaction: discord.Interaction, username: str, tag: str, channel: discord.TextChannel):
    res = riot_api.get_puuid(username, tag)
    if res.status_code == 404:
        await interaction.response.send_message("Account not found", ephemeral=True)
        return
    err = riot_api.status_err(res)
    if not err:
        await interaction.response.send_message(err, ephemeral=True)
        print("Bad status @ riot_api.get_puuid:", err)
        return
    puuid = res.json().puuid
    res = riot_api.get_region(puuid) # hopefully this works flawlessly
    err = riot_api.status_err(res)
    if not err:
        await interaction.response.send_message(err, ephemeral=True)
        print("Bad status @ riot_api.get_region:", err)
        return
    region = res.json().region
    res = riot_api.get_elo(region, puuid)
    err = riot_api.status_err(res)
    if not err:
        await interaction.response.send_message(err, ephemeral=True)
        print("Bad status @ riot_api.get_elo:", err)
        return
    data = api_adapter.convert_ranked_data(next((d for d in res.json() if d["queueType"] == "RANKED_SOLO_5x5"), None))
    try:
        account_dao.add_account(interaction.guild_id, channel.id, puuid, username, tag, data["elo"], data["wins"], data["losses"], region)
        await interaction.response.send_message("Account successfully added", ephemeral=True)
    except sqlite3.IntegrityError:
        await interaction.response.send_message("Account already added to this server", ephemeral=True)
    except sqlite3.Error as e:
        await interaction.response.send_message("Internal error", ephemeral=True)
        print("Error @ account_dao.add_account:", e)
    
@tree.command(name="accountchngchnl", description="Change output channel of account", guilds=GUILD_LIST)
@discord.app_commands.describe(
    puuid="Account to update",
    channel="New output channel"
)
async def account_change_channel(interaction: discord.Interaction, puuid: str, channel: discord.TextChannel):
    try:
        account_dao.update_account_channel(interaction.guild_id, puuid, channel.id)
        await interaction.response.send_message("Output channel successfully changed", ephemeral=True)
    except sqlite3.Error as e:
        await interaction.response.send_message("Internal error", ephemeral=True)
        print("Error @ accountDAAO.update_account_channel:", e)
account_change_channel.autocomplete("puuid")(account_auto_complete)

@tree.command(name="accountrmv", description="Remove account from tracking", guilds=GUILD_LIST)
@discord.app_commands.describe(
    puuid="Account to remove"
)
async def account_remove(interaction: discord.Interaction, puuid: str):
    try:
        account_dao.remove_account(interaction.guild_id, puuid)
        await interaction.response.send_message("Account successfully removed", ephemeral=True)
    except sqlite3.Error as e:
        await interaction.response.send_message("Internal error", ephemeral=True)
        print("Error @ account_dao.remove_account:", e)
account_remove.autocomplete("puuid")(account_auto_complete)