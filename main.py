import asyncio
import signal
import sys
import time
from rich.live import Live
from core.config_loader import assets_config, scanner_config
from core.scanner import VolatilityScanner
from core.logger import logger
from core.display_manager import DisplayManager
from rich.console import Console
import traceback
from threading import Thread, Event

console = Console()
data_updater = None
scan_updater = None

def signal_handler(sig, frame):
    logger.info('You pressed Ctrl+C! Exiting gracefully...')
    global data_updater, scan_updater
    if data_updater:
        data_updater.stop()
    if scan_updater:
        scan_updater.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

initial_prices_updated = Event()

def initial_prices_update(assets):
    async def run_initial_prices_update():
        try:
            scanner = VolatilityScanner(assets)
            await scanner._update_current_prices()
        except Exception as e:
            logger.error(f"Error during initial price update: {e}")
            traceback.print_exc()
        finally:
            initial_prices_updated.set()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_initial_prices_update())
    loop.close()

def initial_scan(assets, scanner):
    async def run_initial_scan():
        try:
            await scanner.scan()
        except Exception as e:
            logger.error(f"Error during initial scan: {e}")
            traceback.print_exc()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_initial_scan())
    loop.close()

class DataUpdaterThread(Thread):
    def __init__(self, scanner):
        super().__init__(daemon=True)
        self.running = True
        self.scanner = scanner

    def run(self):
        async def run_async():
            while self.running:
                try:
                    await asyncio.sleep(scanner_config["intervals"]["data_refresh"])
                    asyncio.run_coroutine_threadsafe(self.scanner._update_current_prices(), asyncio.get_running_loop())
                except Exception as e:
                    logger.error(f"Error during data update: {e}")
                    traceback.print_exc()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_async())
        finally:
            loop.close()

    def stop(self):
        self.running = False

class ScanUpdaterThread(Thread):
    def __init__(self, scanner):
        super().__init__(daemon=True)
        self.running = True
        self.scanner = scanner

    def run(self):
        async def run_async():
            while self.running:
                try:
                    await asyncio.sleep(scanner_config["intervals"]["data_refresh"])
                    asyncio.run_coroutine_threadsafe(self.scanner.scan(), asyncio.get_running_loop())
                except Exception as e:
                    logger.error(f"Error during scan update: {e}")
                    traceback.print_exc()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_async())
        finally:
            loop.close()
    
    def stop(self):
        self.running = False

async def main():
    global data_updater, scan_updater
    display_manager = DisplayManager()
    intervals = scanner_config["intervals"]

    scanner = VolatilityScanner(assets_config)

    # Start initial prices update in a separate thread
    initial_prices_thread = Thread(target=initial_prices_update, args=(assets_config,))
    initial_prices_thread.start()
    initial_prices_updated.wait() #Wait for prices to be updated

    # Start initial scan in a separate thread (NO join here)
    initial_scan_thread = Thread(target=initial_scan, args=(assets_config, scanner))
    initial_scan_thread.start() #Do not join here

    data_updater = DataUpdaterThread(scanner)
    data_updater.start()

    scan_updater = ScanUpdaterThread(scanner)
    scan_updater.start()

    with Live(console=console) as live:
        i = 0
        while True:
            async with VolatilityScanner.cache_lock:
                results = VolatilityScanner.asset_data_cache.copy()
                current_prices = VolatilityScanner.current_prices_cache.copy()

            if current_prices and current_prices.get("prices"): #Check if prices exists
                if results:
                    table = display_manager.display_results(assets_config, results, current_prices)
                    live.update(table)
                else:
                    live.update("Waiting for initial scan...") #Show waiting message
            else:
                live.update("Waiting for prices...") #Show waiting message
            display_refresh = intervals["display_refresh"]
            i = i + 2
            if (i * intervals["display_refresh"]) > intervals["data_refresh"]:
                display_refresh = int(intervals["data_refresh"] / 2) # increase sleep time
            await asyncio.sleep(display_refresh)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        traceback.print_exc()
    finally:
        if data_updater:
            data_updater.stop()
        if scan_updater:
            scan_updater.stop()
        logger.info("Application finished.")