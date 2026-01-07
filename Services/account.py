
import discord
import sqlite3

import config
import helper
from bot import GUILD_LIST, tree
import DAO.accountDAO as accountDAO
import API.riotAPI as riotAPI

async def accountautocomplete(interaction: discord.Interaction, current: str) -> list:
    accounts = accountDAO.get_server_accounts(interaction.guild_id)
    matches = [account for account in accounts if current.lower() in f"{account["username"]}#{account["tag"]}".lower()][:25]
    return [discord.app_commands.Choice(name=f"{account["username"]}#{account["tag"]}", value=account["puuid"]) for account in matches]

@tree.command(name="acountadd", description="Add account to track", guilds=GUILD_LIST)
@discord.app_commands.describe(
    username="Username of account",
    tag="Tag of account",
    channel="Output channel"
)
@discord.app_commands.choices(
    region=[ discord.app_commands.Choice(name=k, value=v) for k, v in config.REGIONS.items() ]
)   
async def accountadd(interaction: discord.Interaction, username: str, tag: str, channel: discord.TextChannel):
    res = riotAPI.get_puuid(username, tag)
    if res.status_code == 404:
        await interaction.response.send_message("Account not found", ephemeral=True)
        return
    default = riotAPI.status_default(res)
    if not default:
        await interaction.response.send_message(default, ephemeral=True)
        print("Bad status @ riotAPI.get_puuid:", default)
        return
    puuid = res.json().puuid
    res = riotAPI.get_region(puuid) # hopefully this works flawlessly
    default = riotAPI.status_default(res)
    if not default:
        await interaction.response.send_message(default, ephemeral=True)
        print("Bad status @ riotAPI.get_region:", default)
        return
    region = res.json().region
    res = riotAPI.get_elo(region, puuid)
    default = riotAPI.status_default(res)
    if not default:
        await interaction.response.send_message(default, ephemeral=True)
        print("Bad status @ riotAPI.get_elo:", default)
        return
    data = next((d for d in res.json() if d["queueType"] == "RANKED_SOLO_5x5"), None)
    elo = helper.get_elo(data["tier"], data["rank"], data["leaguePoints"])
    try:
        accountDAO.add_account(interaction.guild_id, channel.id, puuid, username, tag, elo, data["wins"], data["losses"], region)
        await interaction.response.send_message("Account successfully added", ephemeral=True)
    except sqlite3.IntegrityError:
        await interaction.response.send_message("Account already added to this server", ephemeral=True)
    except sqlite3.Error as e:
        await interaction.response.send_message("Internal error", ephemeral=True)
        print("Error @ accountDAO.add_account:", e)
    
@tree.command(name="accountchngchnl", description="Change output channel of account", guilds=GUILD_LIST)
@discord.app_commands.describe(
    puuid="Account to update",
    channel="New output channel"
)
async def accountchangechannel(interaction: discord.Interaction, puuid: str, channel: discord.TextChannel):
    try:
        accountDAO.update_account_channel(interaction.guild_id, puuid, channel.id)
        await interaction.response.send_message("Output channel successfully changed", ephemeral=True)
    except sqlite3.Error as e:
        await interaction.response.send_message("Internal error", ephemeral=True)
        print("Error @ accountDAAO.update_account_channel:", e)
accountchangechannel.autocomplete("puuid")(accountautocomplete)

@tree.command(name="accountrmv", description="Remove account from tracking", guilds=GUILD_LIST)
@discord.app_commands.describe(
    puuid="Account to remove"
)
async def accountremove(interaction: discord.Interaction, puuid: str):
    try:
        accountDAO.remove_account(interaction.guild_id, puuid)
        await interaction.response.send_message("Account successfully removed", ephemeral=True)
    except sqlite3.Error as e:
        await interaction.response.send_message("Internal error", ephemeral=True)
        print("Error @ accountDAO.remove_account:", e)
accountremove.autocomplete("puuid")(accountautocomplete)