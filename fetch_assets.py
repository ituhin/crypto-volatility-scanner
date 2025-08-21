import requests
import json
import os

def fetch_and_save_perpetual_assets(output_file="config/assets.json"):
    """Fetches perpetual trading pairs from Binance, filters for USDT pairs,
    and saves them to a JSON file.
    """
    try:
        url = "https://fapi.binance.com/fapi/v1/exchangeInfo"  # Futures API endpoint
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes

        exchange_info = response.json()
        symbols = exchange_info.get("symbols", [])

        usdt_pairs = []
        for symbol_info in symbols:
            symbol = symbol_info["symbol"]
            if symbol.endswith("USDT") and symbol_info.get("contractType") == "PERPETUAL" and symbol_info.get("status") == "TRADING":  # Filter for USDT and PERPETUAL
                usdt_pairs.append(symbol)

        filtered_usdt_pairs = filter_usdt_pairs(usdt_pairs, ["BUSD", "TUSD", "USDC", "PAX", "IDRT", "RUB", "TRY", "EUR", "GBP", "JPY", "FDUSD"])
        filtered_usdt_pairs = sorted(filtered_usdt_pairs)

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(filtered_usdt_pairs, f, indent=4)

        print(f"USDT perpetual pairs saved to {output_file}")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Binance: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
    except OSError as e:
        print(f"Error writing to file: {e}")

def filter_usdt_pairs(pairs, filter_list):
    """Filters out USDT pairs that begin with any item from the filter list."""
    filtered_pairs = []
    for pair in pairs:
        if pair.endswith("USDT"):
            base_asset = pair[:-4]  # Remove "USDT" to get the base asset
            if any(base_asset.startswith(f) for f in filter_list):
                continue  # Skip if the base asset starts with a filtered item
            filtered_pairs.append(pair)
    return filtered_pairs

def filter_usdt_pairs_comprehension(pairs, filter_list):
    """Filters out USDT pairs using list comprehension."""
    return [
        pair
        for pair in pairs
        if pair.endswith("USDT") and not any(pair[:-4].startswith(f) for f in filter_list)
    ]

if __name__ == "__main__":
    fetch_and_save_perpetual_assets()