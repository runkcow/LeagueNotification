from dotenv import load_dotenv
import os

from discord import app_commands
import discord
from discord.ext import tasks
from typing import Optional

import io
import requests

load_dotenv(dotenv_path=".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")


