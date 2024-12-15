import json
import os
from discord.ext import tasks
import requests
from config import *
from attack_roasts import roasts, brutal_roasts

TRACKED_ATTACKS_FILE = "tracked_attacks.json"

def load_stars(file_path):
    """Load stars data from a JSON file."""
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return json.load(file)
    return {}

def save_stars(data, file_path):
    """Save stars data to a JSON file."""
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)

def load_tracked_attacks():
    """Load tracked attacks data from a JSON file."""
    if os.path.exists(TRACKED_ATTACKS_FILE):
        with open(TRACKED_ATTACKS_FILE, "r") as file:
            return json.load(file)
    return []

def save_tracked_attacks(data):
    """Save tracked attacks data to a JSON file."""
    with open(TRACKED_ATTACKS_FILE, "w") as file:
        json.dump(data, file, indent=4)

def reset_tracked_attacks():
    """Reset the tracked attacks file by clearing its content."""
    with open(TRACKED_ATTACKS_FILE, "w") as file:
        json.dump([], file)

def update_stars(attacks, stars_data, tracked_attacks):
    """Update the stars data with the results from the current war."""
    for attack in attacks:
        attack_key = (attack["attacker"], attack["defender"])
        if attack_key not in tracked_attacks:
            attacker = attack["attacker"]
            stars = attack["stars"]
            if attacker not in stars_data:
                stars_data[attacker] = 0
            stars_data[attacker] += stars
            tracked_attacks.append(attack_key)
    return stars_data, tracked_attacks

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

async def roast_member(channel, member_name, brutal=False):
    """Send a roast to the specified channel."""
    if not roasting_enabled:
        return

    import random
    roast = random.choice(brutal_roasts if brutal else roasts).format(name=member_name)
    await channel.send(roast)

def get_war_attacks(war_data):
    """Extract attack data from the war."""
    attacks = []
    if "clan" in war_data:
        for member in war_data["clan"].get("members", []):
            member_position = member.get("mapPosition")
            for attack in member.get("attacks", []):
                defender_position = None
                for opponent_member in war_data["opponent"]["members"]:
                    if opponent_member["tag"] == attack.get("defenderTag"):
                        defender_position = opponent_member.get("mapPosition")
                        break
                attacks.append({
                    "attacker": f"{member['name']} (#{member_position})",
                    "stars": attack["stars"],
                    "destruction": attack["destructionPercentage"],
                    "defender": f"{attack.get('defenderTag')} (#{defender_position})"
                })
    return attacks
    
@tasks.loop(minutes=5)
async def check_war_updates():
    """Periodically check for war updates and track attacks."""
    global initialized, last_war_state
    encoded_clan_tag = CLAN_TAG.replace("#", "%23")
    war_data = get_current_war(encoded_clan_tag)

    if not war_data:
        return

    # Load existing war stars, CWL stars, and tracked attacks data
    war_stars_data = load_stars(WAR_STARS_FILE)
    cwl_stars_data = load_stars(CWL_STARS_FILE)
    tracked_attacks = load_tracked_attacks()

    # Initialize last_war_state if it hasn't been set
    current_state = war_data.get("state")
    if last_war_state is None:
        last_war_state = current_state

    # Notify when a new war starts and reset tracked attacks
    if last_war_state != current_state and current_state == "inWar":
        last_war_state = current_state
        reset_tracked_attacks()
        channel = bot.get_channel(WAR_UPDATES_CHANNEL_ID)
        if channel:
            await channel.send("A new war has started! Prepare for battle.")

    if current_state != "inWar":
        return

    # Extract attacks
    attacks = []
    if "rounds" in war_data:  # Handle CWL data
        for round in war_data["rounds"]:
            for war in round.get("wars", []):
                attacks.extend(get_war_attacks(war))
        cwl_stars_data, tracked_attacks = update_stars(attacks, cwl_stars_data, tracked_attacks)
        save_stars(cwl_stars_data, CWL_STARS_FILE)
    else:  # Handle regular war data
        attacks = get_war_attacks(war_data)
        war_stars_data, tracked_attacks = update_stars(attacks, war_stars_data, tracked_attacks)
        save_stars(war_stars_data, WAR_STARS_FILE)

    save_tracked_attacks(tracked_attacks)

    channel = bot.get_channel(WAR_UPDATES_CHANNEL_ID)
    if channel and war_update_setting != "none":
        for attack in attacks:
            attack_key = (attack["attacker"], attack["defender"])
            if attack_key not in tracked_attacks:
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


@bot.tree.command(name="topwarstars", description="Show top members by war stars.")
async def topwarstars(interaction: discord.Interaction, top_n: int = 5):
    """Retrieve top members by cumulative war stars."""
    war_stars_data = load_stars(WAR_STARS_FILE)
    if not war_stars_data:
        await interaction.response.send_message("No war stars data available.", ephemeral=True)
        return

    sorted_stars = sorted(war_stars_data.items(), key=lambda x: x[1], reverse=True)[:top_n]
    leaderboard = "\n".join([f"{i+1}. {name}: {stars} stars" for i, (name, stars) in enumerate(sorted_stars)])
    await interaction.response.send_message(f"**Top {top_n} Members by War Stars:**\n{leaderboard}")

@bot.tree.command(name="topcwlstars", description="Show top members by CWL stars.")
async def topcwlstars(interaction: discord.Interaction, top_n: int = 5):
    """Retrieve top members by cumulative CWL stars."""
    cwl_stars_data = load_stars(CWL_STARS_FILE)
    if not cwl_stars_data:
        await interaction.response.send_message("No CWL stars data available.", ephemeral=True)
        return

    sorted_stars = sorted(cwl_stars_data.items(), key=lambda x: x[1], reverse=True)[:top_n]
    leaderboard = "\n".join([f"{i+1}. {name}: {stars} stars" for i, (name, stars) in enumerate(sorted_stars)])
    await interaction.response.send_message(f"**Top {top_n} Members by CWL Stars:**\n{leaderboard}")
