import requests
from core.logger import logger
import urllib.parse
from utils import mytime_from_timestamp

class BinanceExchange:
    def __init__(self):
        self.base_url = "https://api.binance.com"
        self.future_base_url = "https://fapi.binance.com"
        self.spot_price_ticker = self.base_url + "/api/v3/ticker/price"
        self.future_price_ticker = self.future_base_url + "/fapi/v1/ticker/price"

    def get_current_prices(self):
        try:
            response = requests.get(self.future_price_ticker)
            response.raise_for_status()
            prices = response.json()
            price_dict = {item['symbol']: float(item['price']) for item in prices}
            return price_dict
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching current prices from Binance: {e}")
            return None

    def get_historical_data(self, symbol, startTime, endTime, interval):
        try:
            query_string = urllib.parse.urlencode({
                "symbol": symbol,
                "interval": interval,
                "startTime": startTime,
                "endTime": endTime,
                "limit": 1000
            })
            url = f"{self.future_base_url}/fapi/v1/klines?{query_string}"
            #print(url)
            response = requests.get(url)
            response.raise_for_status()
            klines = response.json()

            historical_data = []
            for kline in klines:
                historical_data.append({
                    "open_time": int(kline[0]),
                    "open": float(kline[1]),
                    "high": float(kline[2]),
                    "low": float(kline[3]),
                    "close": float(kline[4]),
                    "volume": float(kline[5]),
                    "close_time": int(kline[6]),
                    "close_time_local": mytime_from_timestamp(int(kline[6])/1000.0),
                    "base_asset_vol": float(kline[7]),
                    "number_of_trades": int(kline[8]),
                    "taker_buy_vol": float(kline[9]),
                    "taker_buy_base_asset_vol": float(kline[10])
                })
            #print(historical_data)
            return historical_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching historical data from Binance: {e}")
            return None