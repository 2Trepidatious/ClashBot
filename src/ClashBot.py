import discord
from discord.ext import commands, tasks
from discord import app_commands
import requests
from dotenv import load_dotenv
import os
import csv
from datetime import datetime, timedelta
from attack_roasts import roasts, brutal_roasts

# Load environment variables
load_dotenv()
API_KEY = os.getenv("CLASH_API_KEY")
CLAN_TAG = os.getenv("CLAN_TAG")
WAR_UPDATES_CHANNEL_ID = int(os.getenv("WAR_UPDATES_CHANNEL_ID", 0))
GENERAL_BOT_CHANNEL_ID = int(os.getenv("GENERAL_BOT_CHANNEL_ID", 0))
BASE_URL = "https://api.clashofclans.com/v1"
DISCORD_SERVER_ID = int(os.getenv("DISCORD_SERVER_ID", 0))

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


def get_clan_info(clan_tag):
    """Fetch clan information using the Clash of Clans API."""
    url = f"{BASE_URL}/clans/{clan_tag}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        print("Clan Info:", data)
        return data
    else:
        print(f"Error fetching clan info: {response.status_code}, {response.text}")
        return None

def get_clan_member_stats(clan_data):
    """Extract member stats from clan data."""
    members = clan_data.get("memberList", [])
    member_stats = []

    for member in members:
        stats = {
            "Name": member.get("name"),
            "Tag": member.get("tag"),
            "Role": member.get("role"),
            "Donations": member.get("donations"),
            "Donations Received": member.get("donationsReceived"),
            "Trophies": member.get("trophies"),
            "War Stars": member.get("warStars")  # Seasonal war stars
        }
        member_stats.append(stats)

    return member_stats


def save_to_csv(data, filename):
    """Save data to a CSV file."""
    keys = data[0].keys() if data else []
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    print(f"Data saved to {filename}")

def get_current_war(clan_tag):
    """Fetch current war information, including CWL if applicable."""
    url = f"{BASE_URL}/clans/{clan_tag}/currentwar"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        war_data = response.json()
        return war_data 
    elif response.status_code == 404:
        return None  # No current war
    else:
        print(f"Error fetching current war info: {response.status_code}, {response.text}")
        return None


def get_war_attacks(war_data):
    """Extract attack data from the war."""
    attacks = []
    if "clan" in war_data:
        for member in war_data["clan"].get("members", []):
            member_position = member.get("mapPosition")
            for attack in member.get("attacks", []):
                attacks.append({
                    "attacker": member["name"],
                    "attacker_position": member_position,
                    "defender_position": attack.get("defenderTag"),
                    "stars": attack["stars"],
                    "destruction": attack["destructionPercentage"]
                })
    return attacks

async def roast_member(channel, member_name, brutal=False):
    """Send a roast to the specified channel."""
    if not roasting_enabled:
        return

    import random
    roast = random.choice(brutal_roasts if brutal else roasts).format(name=member_name)
    await channel.send(roast)

def get_attack_data(war_data):
    attacks = []
    for member in war_data["clan"].get("members", []):
            for attack in member.get("attacks", []):
                defender_position = None
                for opponent_member in war_data["opponent"]["members"]:
                    if opponent_member["tag"] == attack["defenderTag"]:
                        defender_position = opponent_member["mapPosition"]
                        break
                attacks.append({
                    "attacker": f"{member['name']} (#{member['mapPosition']})",
                    "stars": attack["stars"],
                    "destruction": attack["destructionPercentage"],
                    "defender": f"{attack.get("defenderTag")} (#{defender_position})"
                })
    return attacks

@tasks.loop(minutes=5)
async def check_war_updates():
    """Periodically check for war updates and track attacks, including CWL."""
    global initialized, last_war_state
    encoded_clan_tag = CLAN_TAG.replace("#", "%23")
    war_data = get_current_war(encoded_clan_tag)

    if not war_data:
        return

    # Initialize last_war_state if it hasn't been set
    current_state = war_data.get("state")
    if last_war_state is None:
        last_war_state = current_state

    # Notify when a new war starts
    if last_war_state != current_state and current_state == "inWar":
        last_war_state = current_state
        channel = bot.get_channel(WAR_UPDATES_CHANNEL_ID)
        if channel:
            await channel.send("A new war has started! Prepare for battle.")

    if current_state != "inWar":
        return

    attacks = []
    if "rounds" in war_data:  # Handle CWL data
        for round in war_data["rounds"]:
            for war in round.get("wars", []):
                attacks = get_attack_data(war)

    else:  # Handle regular war data
        attacks = get_attack_data(war_data)

    channel = bot.get_channel(WAR_UPDATES_CHANNEL_ID)
    if channel and war_update_setting != "none":
        for attack in attacks:
            attack_key = (attack["attacker"], attack["defender"])
            if attack_key not in tracked_attacks:
                tracked_attacks.add(attack_key)

                if war_update_setting == "all" or (war_update_setting == "one_zero" and attack["stars"] <= 1):
                    await channel.send(
                        f"**New Attack!**\n"
                        f"Attacker: {attack['attacker']}\n"
                        f"Defender: {attack['defender']}\n"
                        f"Stars: {attack['stars']}\n"
                        f"Destruction: {attack['destruction']}%"
                    )

                    if attack["stars"] == 0:
                        await roast_member(channel, attack["attacker"], brutal=True)
                    elif attack["stars"] == 1:
                        await roast_member(channel, attack["attacker"], brutal=False)

@bot.event
async def on_ready():
    """Start tasks when the bot is ready."""
    print(f"Bot is ready and logged in as {bot.user}")
    if not check_war_updates.is_running():
        check_war_updates.start()

    # Sync slash commands to the specific server
    server = discord.Object(id=DISCORD_SERVER_ID)
    await bot.tree.sync(guild=server)
    print(f"Slash commands synced to server ID: {DISCORD_SERVER_ID}")


@bot.event
async def on_guild_join(discord_server_id: discord.Guild):
    """Sync commands when the bot joins a new Discord server."""
    print(f"Bot added to server: {discord_server_id.name} (ID: {discord_server_id.id})")
    try:
        # Sync commands for the new server
        await bot.tree.sync(guild=discord.Object(id=discord_server_id.id))
        print(f"Slash commands synced for server: {discord_server_id.name} (ID: {discord_server_id.id})")
    except Exception as e:
        print(f"Failed to sync commands for server: {discord_server_id.name} (ID: {discord_server_id.id})\n{e}")

@bot.tree.command(name="toggle_roasts", description="Enable or disable roasts.")
async def toggle_roasts(interaction: discord.Interaction, status: str):
    global roasting_enabled
    if status.lower() in ["on", "off"]:
        roasting_enabled = status.lower() == "on"
        await interaction.response.send_message(f"Roasting has been turned {'on' if roasting_enabled else 'off'}.", ephemeral=True)
    else:
        await interaction.response.send_message("Invalid input. Use '/toggle_roasts on' or '/toggle_roasts off'.", ephemeral=True)

@bot.tree.command(name="set_war_updates", description="Set the type of war updates to display.")
async def set_war_updates(interaction: discord.Interaction, setting: str):
    """Set the type of war updates to show."""
    global war_update_setting
    if setting.lower() in ["all", "one_zero", "none"]:
        war_update_setting = setting.lower()
        await interaction.response.send_message(f"War updates set to: {war_update_setting}", ephemeral=True)
    else:
        await interaction.response.send_message("Invalid setting. Use 'all', 'one_zero', or 'none'.", ephemeral=True)

@bot.tree.command(name="clanstats", description="Retrieve clan statistics.")
async def clanstats(interaction: discord.Interaction):
    if interaction.channel_id != GENERAL_BOT_CHANNEL_ID:
        await interaction.response.send_message("This command is not allowed in this channel.", ephemeral=True)
        return

    encoded_clan_tag = CLAN_TAG.replace("#", "%23")  # URL encode the clan tag
    clan_data = get_clan_info(encoded_clan_tag)

    if not clan_data:
        await interaction.response.send_message("Failed to fetch clan stats.", ephemeral=True)
        return

    clan_summary = (
        f"**Clan Name:** {clan_data.get('name')}\n"
        f"**Clan Level:** {clan_data.get('clanLevel')}\n"
        f"**Members:** {clan_data.get('members')}/50\n"
        f"**Clan Points:** {clan_data.get('clanPoints')}"
    )
    await interaction.response.send_message(clan_summary)


@bot.tree.command(name="memberstats", description="Retrieve stats for a specific member.")
async def memberstats(interaction: discord.Interaction, member_name: str):
    if interaction.channel_id != GENERAL_BOT_CHANNEL_ID:
        await interaction.response.send_message("This command is not allowed in this channel.", ephemeral=True)
        return

    encoded_clan_tag = CLAN_TAG.replace("#", "%23")
    clan_data = get_clan_info(encoded_clan_tag)

    if not clan_data:
        await interaction.response.send_message("Failed to fetch member stats.", ephemeral=True)
        return

    members = get_clan_member_stats(clan_data)
    member = next((m for m in members if m["Name"].lower() == member_name.lower()), None)

    if not member:
        await interaction.response.send_message(f"Member '{member_name}' not found.", ephemeral=True)
        return

    member_summary = (
        f"**Name:** {member['Name']}\n"
        f"**Role:** {member['Role']}\n"
        f"**Donations:** {member['Donations']}\n"
        f"**Donations Received:** {member['Donations Received']}\n"
        f"**Trophies:** {member['Trophies']}\n"
        f"**War Stars:** {member.get("War Stars", 0)}"
    )
    await interaction.response.send_message(member_summary)

@bot.tree.command(name="topwarmembers", description="Retrieve top war members based on season war stars.")
async def topwarmembers(interaction: discord.Interaction, top_n: int = 5):
    """Retrieve top members in the clan based on season war stars."""
    encoded_clan_tag = CLAN_TAG.replace("#", "%23")
    clan_data = get_clan_info(encoded_clan_tag)

    if not clan_data:
        await interaction.response.send_message("Failed to fetch war member stats.", ephemeral=True)
        return

    members = clan_data.get("memberList", [])
    top_members = sorted(members, key=lambda x: x.get("warStars", 0), reverse=True)[:top_n]

    if not top_members:
        await interaction.response.send_message("No war members found.", ephemeral=True)
        return

    member_list = "\n".join(
        [f"{i+1}. {member['name']} - {member.get('warStars', 0)} War Stars" for i, member in enumerate(top_members)]
    )
    await interaction.response.send_message(f"**Top {top_n} War Members:**\n{member_list}")

@bot.tree.command(name="topdonors", description="Retrieve top donors in the clan.")
async def topdonors(interaction: discord.Interaction, top_n: int = 5):
    if interaction.channel_id != GENERAL_BOT_CHANNEL_ID:
        await interaction.response.send_message("This command is not allowed in this channel.", ephemeral=True)
        return

    encoded_clan_tag = CLAN_TAG.replace("#", "%23")
    clan_data = get_clan_info(encoded_clan_tag)

    if not clan_data:
        await interaction.response.send_message("Failed to fetch top donors.", ephemeral=True)
        return

    members = get_clan_member_stats(clan_data)
    top_donors = sorted(members, key=lambda x: x["Donations"], reverse=True)[:top_n]

    if not top_donors:
        await interaction.response.send_message("No donors found.", ephemeral=True)
        return

    donor_list = "\n".join(
        [f"{i+1}. {donor['Name']} - {donor['Donations']} Troops" for i, donor in enumerate(top_donors)]
    )
    await interaction.response.send_message(f"**Top {top_n} Donors:**\n{donor_list}")


@bot.tree.command(name="exportstats", description="Export member stats to a CSV file and provide a download link.")
async def exportstats(interaction: discord.Interaction):
    if interaction.channel_id != GENERAL_BOT_CHANNEL_ID:
        await interaction.response.send_message("This command is not allowed in this channel.", ephemeral=True)
        return

    encoded_clan_tag = CLAN_TAG.replace("#", "%23")
    clan_data = get_clan_info(encoded_clan_tag)

    if not clan_data:
        await interaction.response.send_message("Failed to fetch member stats for export.", ephemeral=True)
        return

    members = get_clan_member_stats(clan_data)
    filename = "clan_member_stats.csv"
    save_to_csv(members, filename)

    await interaction.response.send_message(file=discord.File(filename))


if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))

