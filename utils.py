from datetime import datetime, timedelta, timezone
import numpy as np
import json

def get_interval_seconds(interval):
    """Converts interval string (e.g., "1m", "1h") to seconds."""
    if interval.endswith("m"):
        return int(interval[:-1]) * 60
    elif interval.endswith("h"):
        return int(interval[:-1]) * 60 * 60
    elif interval.endswith("d"):
        return int(interval[:-1]) * 60 * 60 * 24
    elif interval.endswith("w"):
        return int(interval[:-1]) * 60 * 60 * 24 * 7
    elif interval.endswith("M"):
        return int(interval[:-1]) * 60 * 60 * 24 * 30  # Approx month
    else:
        raise ValueError(f"Invalid interval format: {interval}")

def prettify(data):
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            print("Invalid JSON string.")
            return
    print(json.dumps(data, indent=4, sort_keys=True))

def rsi_data_to_json(rsi_data):
    """Converts RSI data to JSON with pretty printing (no pandas)."""
    if rsi_data is None:
        return None

    try:
        # Convert datetime objects (if any) to strings
        json_serializable_data = {}
        for timestamp, data in rsi_data.items():
            if isinstance(timestamp, datetime):  # Check for datetime objects
                timestamp_str = timestamp.isoformat()
            else:
                timestamp_str = str(timestamp) # Convert to string if it is not datetime
            json_serializable_data[timestamp_str] = data
        return json.dumps(json_serializable_data, indent=4)  # Pretty printing
    except (TypeError, OverflowError) as e:
        print(f"Error converting RSI data to JSON: {e}")
        return None

def mytime_from_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def calculate_percentage_change(old_price, current_price):
    if old_price is None or current_price is None or old_price == 0:
        return None
    try:
        return ((current_price - old_price) / old_price) * 100
    except ZeroDivisionError:
        return None

def calculate_volatility(price_changes, std_dev_multiplier):
    """Calculates volatility based on price changes."""
    if not price_changes or any(change is None for change in price_changes):
        return None

    valid_changes = [change for change in price_changes if change is not None]
    if not valid_changes or len(valid_changes) < 2:  # Need at least 2 points for std dev
        return None

    std_dev = np.std(valid_changes)
    if np.isclose(std_dev, 0.0):  # avoid division by zero
        return None
    return std_dev * std_dev_multiplier

def get_time_delta_from_duration_ms(duration_seconds):
    """Converts a duration in seconds to a timedelta object in milliseconds."""
    return timedelta(milliseconds=duration_seconds * 1000)
    
def get_current_utc_timestamp_ms():
    """Returns the current time in UTC as an integer timestamp (milliseconds)."""
    current_time_utc = datetime.now(timezone.utc)
    return int(current_time_utc.timestamp() * 1000)

def convert_ms_timestamp_to_datetime_utc(ms_timestamp):
    """Converts a millisecond timestamp to a UTC datetime object."""
    if ms_timestamp is None:
        return None
    try:
        return datetime.utcfromtimestamp(ms_timestamp / 1000)
    except (OSError, OverflowError, ValueError) as e:  # More robust error handling
        print(f"Timestamp conversion error: {ms_timestamp} - {e}")
        return None
