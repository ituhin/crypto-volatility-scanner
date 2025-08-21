import json
import time
from tradingview_ta import TA_Handler, Interval
from core.logger import logger

MAX_RETRIES = 3
RETRY_DELAY = 1

class TradingViewExchange:
    def __init__(self):  # Removed username and password
        pass

    def get_analysis(self, symbol, interval):
        try:
            exchange, ticker = symbol.split(":")
        except ValueError:
            logger.error(f"Invalid symbol format: {symbol}. Expected 'EXCHANGE:TICKER'.")
            return None

        handler = TA_Handler(symbol=ticker, screener="crypto", exchange=exchange, interval=interval) # Removed username and password

        for _ in range(MAX_RETRIES):
            try:
                analysis = handler.get_analysis()
                if analysis is not None:
                    return analysis
                else:
                    logger.warning(f"Analysis is None for {symbol} on attempt {_ + 1}.")
                    time.sleep(RETRY_DELAY)
            except Exception as e:
                logger.warning(f"Error getting analysis for {symbol} (Retry {_ + 1}/{MAX_RETRIES}): {e}")
                time.sleep(RETRY_DELAY)

        logger.error(f"Failed to get analysis for {symbol} after {MAX_RETRIES} retries.")
        return None

    def get_current_price(self, symbol):
        try:
            exchange, ticker = symbol.split(":")
        except ValueError:
            logger.error(f"Invalid symbol format: {symbol}. Expected 'EXCHANGE:TICKER'.")
            return None

        for _ in range(MAX_RETRIES):
            try:
                handler = TA_Handler(symbol=ticker, screener="crypto", exchange=exchange, interval=Interval.INTERVAL_1_MINUTE) # Removed username and password
                analysis = handler.get_analysis()
                if analysis is not None:
                    if hasattr(analysis, 'close'):
                        return analysis.close
                    elif hasattr(analysis, 'indicators') and isinstance(analysis.indicators, dict) and 'close' in analysis.indicators:
                        return analysis.indicators['close']
                    elif hasattr(analysis, 'ohlc') and isinstance(analysis.ohlc, dict) and 'close' in analysis.ohlc:
                        return analysis.ohlc['close']
                    else:
                        logger.warning(f"Analysis object for {symbol} does not have expected 'close' attribute or structure.")
                        logger.debug(f"Analysis object: {analysis.__dict__ if hasattr(analysis, '__dict__') else analysis}")
                        time.sleep(RETRY_DELAY)
                        continue # continue to next retry
                else:
                    logger.warning(f"Analysis is None for {symbol} on attempt {_ + 1}.")
                    time.sleep(RETRY_DELAY)
                    continue # continue to next retry
            except Exception as e:
                logger.error(f"Error retrieving current price for {symbol}: {e}")
                time.sleep(RETRY_DELAY)
        logger.error(f"Failed to get current price for {symbol} after {MAX_RETRIES} retries.")
        return None

    def get_historical_data(self, symbol, interval, limit):
        logger.debug(f"Fetching historical data for {symbol} with interval {interval} and limit {limit}")
        analysis = self.get_analysis(symbol, interval)
        if analysis:
            logger.debug(f"Analysis object: {json.dumps(analysis.__dict__, default=str) if hasattr(analysis, '__dict__') else analysis}")
            if hasattr(analysis, 'indicators') and analysis.indicators is not None:
                indicators = analysis.indicators
                logger.debug(f"Indicators object: {json.dumps(indicators, default=str) if indicators else indicators}")
                if isinstance(indicators, dict):
                    if "open" in indicators and "high" in indicators and "low" in indicators and "close" in indicators and "volume" in indicators:
                        opens = indicators['open']
                        highs = indicators['high']
                        lows = indicators['low']
                        closes = indicators['close']
                        volumes = indicators['volume']

                        historical_data = []
                        if isinstance(closes, list):
                            data_len = len(closes)
                            if data_len > 0:
                                for i in range(min(data_len, limit)): # Limit the data points
                                    historical_data.append({
                                        'open': opens[i] if isinstance(opens, list) and i < len(opens) else opens,
                                        'high': highs[i] if isinstance(highs, list) and i < len(highs) else highs,
                                        'low': lows[i] if isinstance(lows, list) and i < len(lows) else lows,
                                        'close': closes[i],
                                        'volume': volumes[i] if isinstance(volumes, list) and i < len(volumes) else volumes
                                    })
                            else:
                                logger.debug(f"No data found for {symbol} with interval {interval}.")
                        elif isinstance(closes, (float, int)):
                            historical_data = [{
                                'open': opens,
                                'high': highs,
                                'low': lows,
                                'close': closes,
                                'volume': volumes
                            }]
                        else:
                            logger.error(f"Unexpected data type for 'close' in indicators: {type(closes)}")
                            return None
                        if historical_data:
                            return historical_data
                        else:
                            return None
                    else:
                        logger.error(f"Analysis.indicators for {symbol} is not a dictionary or does not have required keys: {json.dumps(indicators, default=str) if indicators else indicators}")
                        return None
                else:
                    logger.error(f"Analysis object for {symbol} does not have 'indicators' attribute: {json.dumps(analysis.__dict__, default=str) if hasattr(analysis, '__dict__') else analysis}")
                    return None
        else:
            logger.warning(f"Could not get analysis for {symbol}.")
            return None