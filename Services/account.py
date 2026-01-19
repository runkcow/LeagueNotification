
import discord
import sqlite3

from bot import GUILD_LIST, tree
from dao import account_dao
from api import riot_api
from api import api_adapter
import helper

async def account_auto_complete(interaction: discord.Interaction, current: str) -> list:
    accounts = account_dao.get_server_accounts(interaction.guild_id)
    matches = [account for account in accounts if current.lower() in f'{account["username"]}#{account["tag"]}'.lower()][:25]
    return [discord.app_commands.Choice(name=f'{account["username"]}#{account["tag"]}', value=account["puuid"]) for account in matches]

# TODO: combine this into a single ClientSession in riot_api.py
@tree.command(name="accountadd", description="Add account to track", guilds=GUILD_LIST)
@discord.app_commands.describe(
    username="Username of account",
    tag="Tag of account",
    channel="Output channel"
)
async def account_add(interaction: discord.Interaction, username: str, tag: str, channel: discord.TextChannel):
    api = riot_api.RiotApi()
    res = await api.get_puuid(username, tag)
    if res.status == 404:
        await interaction.response.send_message("Account not found", ephemeral=True)
        return
    err = riot_api.status_err(res)
    if not err is None:
        print("Bad status @ account.account_add riot_api.get_puuid:", err)
        await interaction.response.send_message(err, ephemeral=True)
        return
    puuid = res.data["puuid"]
    res = await api.get_region(puuid) # hopefully this works flawlessly
    err = riot_api.status_err(res)
    if not err is None:
        print("Bad status @ account.account_add riot_api.get_region:", err)
        await interaction.response.send_message(err, ephemeral=True)
        return
    region = res.data["region"]
    res = await api.get_elo(region, puuid)
    err = riot_api.status_err(res)
    if not err is None:
        print("Bad status @ account.account_add riot_api.get_elo:", err)
        await interaction.response.send_message(err, ephemeral=True)
        return
    data = api_adapter.convert_ranked_data(next((d for d in res.data if d["queueType"] == "RANKED_SOLO_5x5"), None))
    try:
        account_dao.add_account(interaction.guild_id, channel.id, puuid, username, tag, data["elo"], data["wins"], data["losses"], region)
        await interaction.response.send_message("Account successfully added", ephemeral=True)
    except sqlite3.IntegrityError:
        await interaction.response.send_message("Account already added to this server", ephemeral=True)
    except sqlite3.Error as e:
        print("Error @ account.account_add account_dao.add_account:", e)
        await interaction.response.send_message("Internal error", ephemeral=True)
    finally:
        api.close()
    
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
        print("Error @ account.account_change_channel accountDAO.update_account_channel:", e)
        await interaction.response.send_message("Internal error", ephemeral=True)
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
        print("Error @ account.account_remove account_dao.remove_account:", e)
        await interaction.response.send_message("Internal error", ephemeral=True)
account_remove.autocomplete("puuid")(account_auto_complete)

@tree.command(name="accountelo", description="Display account elo", guilds=GUILD_LIST)
@discord.app_commands.describe(
    puuid="Account to display"
)
async def account_elo(interaction: discord.Interaction, puuid: str):
    try:
        account = account_dao.get_account(puuid)
        if account["wins"] + account["losses"] == 0:
            await interaction.response.send_message(f'Unranked')
        else:
            await interaction.response.send_message(f'{helper.display_elo(account["elo"])}', ephemeral=True)
    except sqlite3.Error as e:
        print("Error @ account.account_elo account_dao.get_account:", e)
        await interaction.response.send_message("Internal error", ephemeral=True)
account_elo.autocomplete("puuid")(account_auto_complete)
