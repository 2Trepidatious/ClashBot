import discord
import requests
import os
import csv
from config import *
from war_updates import check_war_updates, load_stars


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

def save_to_csv(data, filename):
    """Save data to a CSV file."""
    keys = data[0].keys() if data else []
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    print(f"Data saved to {filename}")

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
    """Retrieve stats for a specific clan member."""
    if interaction.channel_id != GENERAL_BOT_CHANNEL_ID:
        await interaction.response.send_message("This command is not allowed in this channel.", ephemeral=True)
        return

    # Fetch clan info
    encoded_clan_tag = CLAN_TAG.replace("#", "%23")
    clan_data = get_clan_info(encoded_clan_tag)

    if not clan_data:
        await interaction.response.send_message("Failed to fetch member stats.", ephemeral=True)
        return

    # Search for the specified member
    members = get_clan_member_stats(clan_data)
    member = next((m for m in members if m["Name"].lower() == member_name.lower()), None)

    if not member:
        await interaction.response.send_message(f"Member '{member_name}' not found.", ephemeral=True)
        return

    # Load stars data
    war_stars_data = load_stars(WAR_STARS_FILE)
    cwl_stars_data = load_stars(CWL_STARS_FILE)

    # Get war stars and CWL stars for the member
    war_stars = war_stars_data.get(member["Name"], 0)
    cwl_stars = cwl_stars_data.get(member["Name"], 0)

    # Construct the response message
    member_summary = (
        f"**Name:** {member['Name']}\n"
        f"**Role:** {member['Role']}\n"
        f"**Donations:** {member['Donations']}\n"
        f"**Donations Received:** {member['Donations Received']}\n"
        f"**Trophies:** {member['Trophies']}\n"
        f"**War Stars:** {war_stars}\n"
        f"**CWL Stars:** {cwl_stars}"
    )
    await interaction.response.send_message(member_summary)


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

