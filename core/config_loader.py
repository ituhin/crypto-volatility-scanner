import json
import os

CONFIG_DIR = "config"

def load_config(filename):
    filepath = os.path.join(CONFIG_DIR, filename)
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file '{filename}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in '{filename}'.")
        return None

assets_config = load_config("assets.json")
scanner_config = load_config("scanner_config.json")
#ta_assets_config = load_config("ta.json")

if not assets_config or not scanner_config:
    exit(1)