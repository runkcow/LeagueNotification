
import discord
import sqlite3

from bot import GUILD_LIST, tree
from dao import account_dao
from api.riot_api import riot_api, status_err
from api import api_adapter
import helper

async def account_auto_complete(interaction: discord.Interaction, current: str) -> list:
    accounts = account_dao.get_server_accounts(interaction.guild_id)
    matches = [account for account in accounts if current.lower() in f'{account["username"]}#{account["tag"]}'.lower()][:25]
    return [discord.app_commands.Choice(name=f'{account["username"]}#{account["tag"]}', value=account["puuid"]) for account in matches]

# TODO: combine this into a single ClientSession in riot_api.py
@tree.command(name="accadd", description="Add account to track", guilds=GUILD_LIST)
@discord.app_commands.describe(
    username="Username of account",
    tag="Tag of account",
    channel="Output channel"
)
async def account_add(interaction: discord.Interaction, username: str, tag: str, channel: discord.TextChannel):
    # get puuid
    res = await riot_api.get_puuid(username, tag)
    if not res.success:
        await interaction.response.send_message(status_err(res), ephemeral=True)
        return
    puuid = res.data
    # get region
    res = await riot_api.get_region(puuid)
    if not res.success:
        await interaction.response.send_message(status_err(res), ephemeral=True)
        return
    region = res.data
    # get elo
    res = await riot_api.get_elo(region, puuid)
    if not res.success:
        await interaction.response.send_message(status_err(res), ephemeral=True)
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
    
@tree.command(name="accchngchnl", description="Change output channel of account", guilds=GUILD_LIST)
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

@tree.command(name="accrmv", description="Remove account from tracking", guilds=GUILD_LIST)
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

@tree.command(name="accelo", description="Display account elo", guilds=GUILD_LIST)
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
