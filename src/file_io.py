import json
import os

def load_file_data(file_path):
    """Load data from a JSON file."""
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return json.load(file)
    return {}

def save_file_data(data, file_path):
    """Save data to a JSON file."""
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)

def reset_file_data(file_path):
    """Reset a JSON data file by clearing its content."""
    with open(file_path, "w") as file:
        json.dump({}, file)