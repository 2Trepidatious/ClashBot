import discord
import requests
import os
import csv
from config import *
from war_updates import check_war_updates
from file_io import *


def get_clan_info(clan_tag):
    """Fetch clan information using the Clash of Clans API."""
    url = f"{BASE_URL}/clans/{clan_tag}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        #print("Clan Info:", data)
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
    """Retrieve and display clan statistics."""
    encoded_clan_tag = CLAN_TAG.replace("#", "%23")
    clan_data = get_clan_info(encoded_clan_tag)

    if not clan_data:
        await interaction.response.send_message("Failed to fetch clan stats.", ephemeral=True)
        return

    # Extract relevant clan data
    clan_name = clan_data.get("name", "Unknown")
    clan_level = clan_data.get("clanLevel", 0)
    members = len(clan_data.get("memberList", []))
    war_wins = clan_data.get("warWins", 0)
    war_ties = clan_data.get("warTies", 0)
    war_losses = clan_data.get("warLosses", 0)
    war_league = clan_data.get("warLeague", {}).get("name", "Unknown")
    capital_league = clan_data.get("capitalLeague", {}).get("name", "Unknown")

    # Format and send response
    response = (
        f"**Clan Name:** {clan_name}\n"
        f"**Clan Level:** {clan_level}\n"
        f"**Members:** {members}\n"
        f"**War League:** {war_league}\n"
        f"**Capital League:** {capital_league}\n"
        f"**War Stats:**\n"
        f"  Wins: {war_wins}\n"
        f"  Ties: {war_ties}\n"
        f"  Losses: {war_losses}\n"
    )

    await interaction.response.send_message(response)


@bot.tree.command(name="memberstats", description="Retrieve stats for a specific member.")
async def memberstats(interaction: discord.Interaction, member_name: str):
    """Retrieve detailed stats for a specific member, including recent attacks."""
    if interaction.channel_id != GENERAL_BOT_CHANNEL_ID:
        await interaction.response.send_message("This command is not allowed in this channel.", ephemeral=True)
        return

    # Load data files
    war_stars_data = load_file_data(WAR_STARS_FILE)
    cwl_stars_data = load_file_data(CWL_STARS_FILE)
    recent_war_data = load_file_data(RECENT_WAR_FILE)
    recent_cwl_data = load_file_data(RECENT_CWL_FILE)

    # Get member data from the clan's API
    encoded_clan_tag = CLAN_TAG.replace("#", "%23")
    clan_data = get_clan_info(encoded_clan_tag)
    if not clan_data:
        await interaction.response.send_message("Failed to fetch member stats.", ephemeral=True)
        return

    # Locate the member in the clan data
    member = next((m for m in clan_data.get("memberList", []) if m["name"].lower() == member_name.lower()), None)
    if not member:
        await interaction.response.send_message(f"Member '{member_name}' not found.", ephemeral=True)
        return

    # Collect general stats
    role = member.get("role", "Unknown").capitalize()
    town_hall_level = member.get("townHallLevel", "Unknown")
    donations = member.get("donations", 0)
    donations_received = member.get("donationsReceived", 0)
    trophies = member.get("trophies", 0)
    war_stars = war_stars_data.get(member_name, 0)
    cwl_stars = cwl_stars_data.get(member_name, 0)

    # Collect recent war attacks
    recent_war_attacks = [
        attack for attack in recent_war_data.values()
        if attack["attacker"].startswith(member_name)
    ]

    # Collect recent CWL attacks with round information
    recent_cwl_attacks = {}
    for round_name, round_attacks in recent_cwl_data.items():
        member_attacks = [
            attack for attack in round_attacks
            if attack["attacker"].startswith(member_name)
        ]
        if member_attacks:
            recent_cwl_attacks[round_name] = member_attacks

    # Helper function to format attack data
    def format_attacks(attacks):
        if not attacks:
            return "No recent attacks."
        return "\n".join(
            f"**Attacked:** {attack['defender']} - **Stars:** {attack['stars']} - "
            f"**Destruction:** {attack['destruction']}%"
            for attack in attacks
        )

    # Format recent attack summaries
    recent_war_summary = format_attacks(recent_war_attacks)
    recent_cwl_summary = (
        "\n".join(
            f"**{round_name}:**\n{format_attacks(round_attacks)}"
            for round_name, round_attacks in recent_cwl_attacks.items()
        )
        if recent_cwl_attacks
        else "No recent CWL attacks."
    )

    # Build and send the response
    response = (
        f"**Stats for {member_name}:**\n"
        f"**Role:** {role}\n"
        f"**Town Hall Level:** {town_hall_level}\n"
        f"**Donations:** {donations}\n"
        f"**Donations Received:** {donations_received}\n"
        f"**Trophies:** {trophies}\n"
        f"**War Stars:** {war_stars}\n"
        f"**CWL Stars:** {cwl_stars}\n\n"
        f"**Recent War Attacks:**\n{recent_war_summary}\n\n"
        f"**Recent CWL Attacks:**\n{recent_cwl_summary}"
    )

    await interaction.response.send_message(response)


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


@bot.tree.command(name="exportstats", description="Export clan stats to a CSV file.")
async def exportstats(interaction: discord.Interaction):
    """Export stats of all clan members to a CSV file."""
    # Load data files
    war_stars_data = load_file_data(WAR_STARS_FILE)
    cwl_stars_data = load_file_data(CWL_STARS_FILE)
    recent_war_data = load_file_data(RECENT_WAR_FILE)
    recent_cwl_data = load_file_data(RECENT_CWL_FILE)

    # Get clan data
    encoded_clan_tag = CLAN_TAG.replace("#", "%23")
    clan_data = get_clan_info(encoded_clan_tag)
    if not clan_data:
        await interaction.response.send_message("Failed to fetch clan stats.", ephemeral=True)
        return

    # Prepare CSV data
    csv_data = []
    for member in clan_data.get("memberList", []):
        member_name = member["name"]
        role = member.get("role", "Unknown").capitalize()
        town_hall_level = member.get("townHallLevel", 0)
        donations = member.get("donations", 0)
        donations_received = member.get("donationsReceived", 0)
        trophies = member.get("trophies", 0)

        # Retrieve cumulative stars
        war_stars = war_stars_data.get(member_name, 0)
        cwl_stars = cwl_stars_data.get(member_name, 0)

        # Retrieve stars from recent war
        recent_war_stars = sum(
            attack["stars"]
            for attack in recent_war_data.values()
            if attack["attacker"].startswith(member_name)
        )

        # Retrieve stars from recent CWL
        recent_cwl_stars = sum(
            attack["stars"]
            for round_attacks in recent_cwl_data.values()
            for attack in round_attacks
            if attack["attacker"].startswith(member_name)
        )

        # Add member data to CSV row
        csv_data.append({
            "Name": member_name,
            "Role": role,
            "Town Hall Level": town_hall_level,
            "Donations": donations,
            "Donations Received": donations_received,
            "Trophies": trophies,
            "Cumulative War Stars": war_stars,
            "Cumulative CWL Stars": cwl_stars,
            "Recent War Stars": recent_war_stars,
            "Recent CWL Stars": recent_cwl_stars,
        })

    # Write to a CSV file with utf-8 encoding
    file_path = "clan_stats.csv"
    with open(file_path, "w", newline="", encoding="utf-8") as csv_file:
        fieldnames = [
            "Name", "Role", "Town Hall Level", "Donations", "Donations Received",
            "Trophies", "Cumulative War Stars", "Cumulative CWL Stars",
            "Recent War Stars", "Recent CWL Stars"
        ]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)

    # Notify user and upload file
    await interaction.response.send_message("Stats exported successfully. Here is the CSV file:", ephemeral=True)
    await interaction.followup.send(file=discord.File(file_path))

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))

