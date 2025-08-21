import asyncio
from datetime import datetime
from utils import prettify, rsi_data_to_json, calculate_percentage_change, calculate_volatility, get_current_utc_timestamp_ms, convert_ms_timestamp_to_datetime_utc
from core.config_loader import scanner_config
from core.logger import logger
from exchanges.binance import BinanceExchange
#from core.ta import calculate_rsi

class VolatilityScanner:
    cache_lock = asyncio.Lock()
    current_prices_cache = {}  # Class-level cache
    asset_data_cache = {}      # Class-level cache

    def __init__(self, assets):
        self.assets = assets
        self.exchange = BinanceExchange()
        self.columns_config = scanner_config["columns"]
        self.config = scanner_config
        self.intervals = scanner_config["intervals"]
        self.volatility_config = self.config["volatility_calculation"]

    async def _update_current_prices(self):
        prices = self.exchange.get_current_prices()
        if prices:
            current_timestamp_ms = get_current_utc_timestamp_ms()
            async with VolatilityScanner.cache_lock:
                if "prices" not in VolatilityScanner.current_prices_cache:
                    VolatilityScanner.current_prices_cache["prices"] = {}

                for asset in self.assets:
                    binance_asset = asset.replace("BINANCE:", "")
                    if binance_asset in prices:
                        if binance_asset not in VolatilityScanner.current_prices_cache["prices"]:
                            VolatilityScanner.current_prices_cache["prices"][binance_asset] = []

                        VolatilityScanner.current_prices_cache["prices"][binance_asset].append({"price": prices[binance_asset], "timestamp": current_timestamp_ms})

                VolatilityScanner.current_prices_cache["timestamp"] = current_timestamp_ms
            logger.debug(f"Current prices cache updated")
            #logger.debug(f"Current prices cache updated: {VolatilityScanner.current_prices_cache}")
        else:
            logger.error("Failed to update current prices cache.")
    
    
    async def _get_current_price(self, asset):
        """Retrieves the current price for an asset from the cache."""
        async with VolatilityScanner.cache_lock:
            current_prices_data = VolatilityScanner.current_prices_cache.copy()
            prices = current_prices_data.get("prices", {})

        if asset not in prices or not prices[asset]:
            logger.info(f"No price data found for {asset}")
            return None

        current_price_data = prices[asset][-1]
        current_price = current_price_data.get("price")
        if current_price is None:
            logger.error(f"current_price is None for {asset}")
            return None
        return current_price
    
    async def _calculate_volatility_for_kline(self, historical_data, interval_in_seconds, duration):
        """Calculates volatility for a given duration."""
        num_data_points = duration // interval_in_seconds
        if num_data_points > len(historical_data):
            return None

        close_prices = [float(kline['close']) for kline in historical_data[-num_data_points:]]
        
        price_changes = []
        for i in range(len(close_prices) - 1):
            change = calculate_percentage_change(close_prices[i], close_prices[i+1])
            if change is not None:
                price_changes.append(change)

        volatility = calculate_volatility(price_changes, self.volatility_config["std_dev_multiplier"])
        return volatility

    async def _get_historical_data_from_exchange(self, asset, durations, current_timestamp_ms):
        if not durations:
            return None

        longest_duration = max(durations)
        interval = "5m" if longest_duration < 24 * 60 * 60 else "30m"
        end_timestamp_ms = current_timestamp_ms
        interval_in_seconds = 5 * 60 if interval == "5m" else 30 * 60
        start_timestamp_ms = end_timestamp_ms - ((longest_duration + interval_in_seconds) * 1000)

        historical_data = self.exchange.get_historical_data(asset, start_timestamp_ms, end_timestamp_ms, interval=interval)

        if historical_data is None or len(historical_data) == 0:
            logger.info(f"No historical data found for {asset}, interval: {interval}")
            return None

        historical_data_for_durations = {}
        for duration in durations:
            try:
                volatility = await self._calculate_volatility_for_kline(historical_data, interval_in_seconds, duration)
                index_diff = (longest_duration - duration) // interval_in_seconds
                kline = historical_data[index_diff]
                historical_data_for_durations[duration] = {**kline, "volatility": volatility}
            except IndexError:
                logger.info(f"Not enough historical data for {asset}, duration: {duration}")
                historical_data_for_durations[duration] = None

        return historical_data_for_durations
    
    async def _get_historical_data_from_exchange1(self, asset, durations, current_timestamp_ms):
        """Fetches historical data from the exchange for a given list of durations and calculates volatility."""
        if not durations:
            return None

        longest_duration = max(durations)
        interval = "5m" if longest_duration < 24 * 60 * 60 else "30m"
        end_timestamp_ms = current_timestamp_ms
    
        interval_in_seconds = 5 * 60 if interval == "5m" else 30 * 60
        start_timestamp_ms = end_timestamp_ms - ((longest_duration + interval_in_seconds) * 1000)

        historical_data = self.exchange.get_historical_data(asset, start_timestamp_ms, end_timestamp_ms, interval=interval)

        if historical_data is None or len(historical_data) == 0:
            logger.info(f"No historical data found for {asset}, interval: {interval}")
            return None
        #rsi_data = calculate_rsi(historical_data, interval)
        #print(asset, historical_data)
        historical_data_for_durations = {}
        for duration in durations:
            index_diff = (longest_duration - duration) // interval_in_seconds
            #print(duration, longest_duration, interval_in_seconds, '--', index_diff)
            try:
                kline = historical_data[index_diff]
                close_prices_for_volatility = []
                for i in range(index_diff, len(historical_data)):
                  close_prices_for_volatility.append(float(historical_data[i]['close']))

                volatility = None
                if len(close_prices_for_volatility) > 1:
                    price_changes = [calculate_percentage_change(close_prices_for_volatility[i], float(kline['close'])) for i in range(len(close_prices_for_volatility))]
                    volatility = calculate_volatility(price_changes, duration, self.volatility_config["std_dev_multiplier"])
                else:
                    logger.info(f"Not enough historical data for volatility calculation for {asset}, duration: {duration}")

                historical_data_for_durations[duration] = {**kline, "volatility": volatility}

            except IndexError:
                logger.info(f"Not enough historical data for {asset}, duration: {duration}")
                historical_data_for_durations[duration] = None

        return historical_data_for_durations

    async def _get_historical_data_for_durations(self, asset, current_timestamp_ms, durations):
        """Retrieves historical data for multiple durations."""
        short_durations = [d for d in durations if d < 24 * 60 * 60]
        long_durations = [d for d in durations if d >= 24 * 60 * 60]

        all_historical_data = {}

        short_data = await self._get_historical_data_from_exchange(asset, short_durations, current_timestamp_ms)
        long_data = await self._get_historical_data_from_exchange(asset, long_durations, current_timestamp_ms)

        if short_data is None and long_data is None:
            return None

        if short_data:
            all_historical_data.update(short_data)
        if long_data:
            all_historical_data.update(long_data)

        return all_historical_data

    async def scan_asset(self, asset, current_timestamp_ms):
        asset_data = {}

        current_price = await self._get_current_price(asset)
        if current_price is None:
            for column in self.columns_config:
                asset_data[column["name"]] = {"percentage": None, "volatility": None, "old_price": None, "old_timestamp": None, "old_datetime": None}
            return {asset: asset_data}

        durations = [int(column["duration"]) for column in self.columns_config]
        historical_data_for_durations = await self._get_historical_data_for_durations(asset, current_timestamp_ms, durations)

        if historical_data_for_durations is None:
            for column in self.columns_config:
                asset_data[column["name"]] = {"percentage": None, "volatility": None, "old_price": None, "old_timestamp": None, "old_datetime": None}
            return {asset: asset_data}

        for column in self.columns_config:
            duration = int(column["duration"])
            kline_data = historical_data_for_durations.get(duration)

            if kline_data is None:
                asset_data[column["name"]] = {"percentage": None, "volatility": None, "old_price": None, "old_timestamp": None, "old_datetime": None}
                continue

            try:
                oldest_timestamp_ms = kline_data.get('close_time')
                #oldest_datetime = convert_ms_timestamp_to_datetime_utc(oldest_timestamp_ms)
                oldest_price = float(kline_data['close'])
                oldest_timestamp = oldest_timestamp_ms / 1000
                volatility = kline_data.get("volatility")

                percentage_change = calculate_percentage_change(oldest_price, current_price)

                asset_data[column["name"]] = {
                    "percentage": f"{percentage_change:.1f}",
                    "volatility": f"{volatility:.2f}" if volatility is not None else None,
                    "old_price": oldest_price,
                    "old_timestamp": oldest_timestamp,
                    #"old_datetime": oldest_datetime
                }
               
            except (IndexError, KeyError, TypeError, ValueError) as e:
                logger.error(f"Error processing historical data: {e}, Data: {kline_data} for {asset}, {column['name']}")
                continue

        #print(asset, '==', current_price)
        #pretty_json(historical_data_for_durations)
        #pretty_json(asset_data)

        return {asset: asset_data}

    async def scan(self):
        logger.info("Starting scan...")
        async with VolatilityScanner.cache_lock:
            current_prices_data = VolatilityScanner.current_prices_cache.copy()
            current_timestamp_ms = current_prices_data.get("timestamp")

        for asset in self.assets:
            asset_data = await self.scan_asset(asset, current_timestamp_ms)
            if asset_data:
                async with VolatilityScanner.cache_lock:
                    VolatilityScanner.asset_data_cache.update(asset_data) #Update cache incrementally
                #logger.info(f"Updated cache for {asset}")
                #logger.info(f"Updated cache for {asset}: {asset_data}") #Log each update
        logger.info("Scan finished.")