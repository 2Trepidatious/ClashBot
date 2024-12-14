import os
from dotenv import load_dotenv
import discord
from discord import app_commands

# Load environment variables
load_dotenv()

# Constants for shared configuration
API_KEY = os.getenv("CLASH_API_KEY")
CLAN_TAG = os.getenv("CLAN_TAG")
WAR_UPDATES_CHANNEL_ID = int(os.getenv("WAR_UPDATES_CHANNEL_ID", 0))
GENERAL_BOT_CHANNEL_ID = int(os.getenv("GENERAL_BOT_CHANNEL_ID", 0))
DISCORD_SERVER_ID = int(os.getenv("DISCORD_SERVER_ID", 0))
BASE_URL = "https://api.clashofclans.com/v1"

if not DISCORD_SERVER_ID:
    raise ValueError("Discord Server ID is not set in the .env file")

if not API_KEY:
    raise ValueError("Clash API Key is not set in the .env file")

if not CLAN_TAG:
    raise ValueError("Clan Tag is not set in the .env file")

# Headers for API authentication
HEADERS = {
    "Authorization": f"Bearer {API_KEY}"
}

intents = discord.Intents.default()
intents.message_content = True

class ClashBot(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

bot = ClashBot(intents=intents)


# In-memory storage for tracking war data
tracked_attacks = set()
roasting_enabled = True
initialized = False
last_war_state = None