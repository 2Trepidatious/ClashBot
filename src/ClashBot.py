import discord
from discord.ext import commands, tasks
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
bot = commands.Bot(command_prefix="/", intents=intents)

# In-memory storage for tracking war data
tracked_attacks = set()
roasting_enabled = True
initialized = False


def get_clan_info(clan_tag):
    """Fetch clan information using the Clash of Clans API."""
    url = f"{BASE_URL}/clans/{clan_tag}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
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
            "War Stars": member.get("warStars")
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
    """Fetch current war information."""
    url = f"{BASE_URL}/clans/{clan_tag}/currentwar"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
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

@tasks.loop(minutes=5)
async def check_war_updates():
    """Periodically check for war updates and track attacks."""
    global initialized
    encoded_clan_tag = CLAN_TAG.replace("#", "%23")
    war_data = get_current_war(encoded_clan_tag)

    if war_data and war_data.get("state") == "inWar":
        attacks = get_war_attacks(war_data)

        for attack in attacks:
            attack_key = (attack["attacker"], attack["defender_position"])
            if attack_key not in tracked_attacks:
                tracked_attacks.add(attack_key)
                if initialized:  # Only notify for new attacks after initialization
                    channel = bot.get_channel(WAR_UPDATES_CHANNEL_ID)
                    if channel:
                        await channel.send(
                            f"**New Attack!**\n"
                            f"Attacker: {attack['attacker']} (#{attack['attacker_position']})\n"
                            f"Defender: #{attack['defender_position']}\n"
                            f"Stars: {attack['stars']}\n"
                            f"Destruction: {attack['destruction']}%"
                        )
                        if attack["stars"] == 0:
                            await roast_member(channel, attack["attacker"], brutal=True)
                        elif attack["stars"] == 1:
                            await roast_member(channel, attack["attacker"], brutal=False)
    initialized = True

@bot.event
async def on_ready():
    """Start tasks when the bot is ready."""
    print(f"Bot is ready and logged in as {bot.user}")
    if not check_war_updates.is_running():
        check_war_updates.start()

@bot.command()
async def toggle_roasts(ctx, status: str):
    """Enable or disable roasts."""
    global roasting_enabled
    if status.lower() in ["on", "off"]:
        roasting_enabled = status.lower() == "on"
        await ctx.send(f"Roasting has been turned {'on' if roasting_enabled else 'off'}.")
    else:
        await ctx.send("Invalid input. Use '/toggle_roasts on' or '/toggle_roasts off'.")

@bot.command()
async def clanstats(ctx):
    """Retrieve clan statistics."""
    if ctx.channel.id != GENERAL_BOT_CHANNEL_ID:
        await ctx.send("This command is not allowed in this channel.")
        return

    encoded_clan_tag = CLAN_TAG.replace("#", "%23")  # URL encode the clan tag
    clan_data = get_clan_info(encoded_clan_tag)

    if not clan_data:
        await ctx.send("Failed to fetch clan stats.")
        return

    clan_summary = (
        f"**Clan Name:** {clan_data.get('name')}\n"
        f"**Clan Level:** {clan_data.get('clanLevel')}\n"
        f"**Members:** {clan_data.get('members')}/50\n"
        f"**Clan Points:** {clan_data.get('clanPoints')}"
    )
    await ctx.send(clan_summary)

@bot.command()
async def memberstats(ctx, member_name: str):
    """Retrieve stats for a specific member."""
    if ctx.channel.id != GENERAL_BOT_CHANNEL_ID:
        await ctx.send("This command is not allowed in this channel.")
        return

    encoded_clan_tag = CLAN_TAG.replace("#", "%23")
    clan_data = get_clan_info(encoded_clan_tag)

    if not clan_data:
        await ctx.send("Failed to fetch member stats.")
        return

    members = get_clan_member_stats(clan_data)
    member = next((m for m in members if m["Name"].lower() == member_name.lower()), None)

    if not member:
        await ctx.send(f"Member '{member_name}' not found.")
        return

    member_summary = (
        f"**Name:** {member['Name']}\n"
        f"**Role:** {member['Role']}\n"
        f"**Donations:** {member['Donations']}\n"
        f"**Donations Received:** {member['Donations Received']}\n"
        f"**Trophies:** {member['Trophies']}\n"
        f"**War Stars:** {member['War Stars']}"
    )
    await ctx.send(member_summary)

@bot.command()
async def topdonors(ctx, top_n: int = 5):
    """Retrieve top donors in the clan."""
    if ctx.channel.id != GENERAL_BOT_CHANNEL_ID:
        await ctx.send("This command is not allowed in this channel.")
        return

    encoded_clan_tag = CLAN_TAG.replace("#", "%23")
    clan_data = get_clan_info(encoded_clan_tag)

    if not clan_data:
        await ctx.send("Failed to fetch top donors.")
        return

    members = get_clan_member_stats(clan_data)
    top_donors = sorted(members, key=lambda x: x["Donations"], reverse=True)[:top_n]

    if not top_donors:
        await ctx.send("No donors found.")
        return
    donor_list = "\n".join(
        [f"{i+1}. {donor['Name']} - {donor['Donations']} Troops" for i, donor in enumerate(top_donors)]
    )
    await ctx.send(f"**Top {top_n} Donors:**\n{donor_list}")

@bot.command()
async def exportstats(ctx):
    """Export member stats to a CSV file and provide a download link."""
    if ctx.channel.id != GENERAL_BOT_CHANNEL_ID:
        await ctx.send("This command is not allowed in this channel.")
        return

    encoded_clan_tag = CLAN_TAG.replace("#", "%23")
    clan_data = get_clan_info(encoded_clan_tag)

    if not clan_data:
        await ctx.send("Failed to fetch member stats for export.")
        return

    members = get_clan_member_stats(clan_data)
    filename = "clan_member_stats.csv"
    save_to_csv(members, filename)

    await ctx.send(file=discord.File(filename))

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))

