import requests
from dotenv import load_dotenv
import os
import csv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("CLASH_API_KEY")
CLAN_TAG = os.getenv("CLASH_CLAN_TAG")
BASE_URL = "https://api.clashofclans.com/v1"

if not API_KEY:
    raise ValueError("Clash API Key is not set in the .env file")

if not CLAN_TAG:
    raise ValueError("Clan Tag is not set in the .env file")

# Headers for API authentication
HEADERS = {
    "Authorization": f"Bearer {API_KEY}"
}

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

def main():
    """Main function to pull clan and member stats."""
    encoded_clan_tag = CLAN_TAG.replace("#", "%23")  # URL encode the clan tag

    # Fetch clan information
    clan_data = get_clan_info(encoded_clan_tag)

    if not clan_data:
        print("Failed to fetch clan data.")
        return

    # Display clan summary
    print(f"Clan Name: {clan_data.get('name')}")
    print(f"Clan Level: {clan_data.get('clanLevel')}")
    print(f"Members: {clan_data.get('members')}/50")
    print(f"Clan Points: {clan_data.get('clanPoints')}")

    # Fetch member stats
    member_stats = get_clan_member_stats(clan_data)

    # Display top donors
    top_donors = sorted(member_stats, key=lambda x: x["Donations"], reverse=True)[:5]
    print("\nTop 5 Donors:")
    for i, donor in enumerate(top_donors, start=1):
        print(f"{i}. {donor['Name']} - {donor['Donations']} Troops")

    # Save stats to CSV
    save_to_csv(member_stats, "clan_member_stats.csv")

if __name__ == "__main__":
    main()
