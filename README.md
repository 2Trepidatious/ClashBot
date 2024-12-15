# ClashBot: Discord Bot for Clash of Clans Clan Management

ClashBot is a Discord bot designed to help Clash of Clans clans manage their wars, members, and statistics more effectively. The bot uses the Clash of Clans API to fetch real-time data and integrates seamlessly into a Discord server for communication and updates.

## Features

### Core Functionality
- **Clan Statistics**: Retrieve and display overall clan statistics such as clan name, level, points, and member count.
- **Member Statistics**: Fetch individual member stats including donations, trophies, war stars, and more.
- **Top Donors**: View the top donors in the clan.
- **Export Stats**: Export member statistics to a CSV file for further analysis.
- **War Updates**: Periodically check for new war attacks and post updates in a specified Discord channel.

### Roasting Features
- **Normal Roasts**: Roast members who achieve 1-star attacks with a humorous response.
- **Brutal Roasts**: Deliver harsher roasts for members who score 0-star attacks.
- **Toggleable Roasts**: Enable or disable roasts using a simple Discord command.

---

## Commands

### General Commands
- `/clanstats`  
  Fetch and display overall clan statistics.
  
- `/memberstats [member_name]`  
  Retrieve stats for a specific clan member.

- `/topdonors [top_n=5]`  
  Show the top donors in the clan. Optionally specify how many top donors to display.

- `/exportstats`  
  Export member statistics to a CSV file and provide a downloadable link.

### Roasting Commands
- `/toggle_roasts [on/off]`  
  Enable or disable roasting features.

---

## Setup Instructions

### Prerequisites
1. Install Python 3.8+.
2. Install the required Python packages:
   ```bash
   pip install discord.py python-dotenv requests discord
   ```
3. Set up a Clash of Clans API key by creating an account on the Clash of Clans Developer Portal.

### Environment Variables
Create a `.env` file in the project root with the following contents:

```env
DISCORD_BOT_TOKEN=your_discord_bot_token
CLASH_API_KEY=your_clash_api_key
CLAN_TAG=#your_clan_tag
WAR_UPDATES_CHANNEL_ID=your_war_updates_channel_id
GENERAL_BOT_CHANNEL_ID=your_general_bot_channel_id
DISCORD_GUILD_ID=your_guild_id
```

Replace the placeholder values with:
- `your_discord_bot_token`: The token for your Discord bot.
- `your_clash_api_key`: The API key from the Clash of Clans Developer Portal.
- `#your_clan_tag`: Your clan's tag, including the leading `#`.
- `your_war_updates_channel_id`: The Discord channel ID where war updates will be posted.
- `your_general_bot_channel_id`: The Discord channel ID for general bot commands.
- `your_discord_server_id`: The ID for your discord server/guild

### Running the Bot
Run the bot script using Python:
```bash
python ClashBot.py
```
Ensure that all required dependencies are installed, and the `.env` file is properly configured.

## File Structure
```plaintext
project_root/
├── attack_roasts.py    # Contains normal and brutal roast lists
├── clash_clan_info.py  # Main bot script
├── .env                # Environment variables
├── requirements.txt    # Python dependencies
```