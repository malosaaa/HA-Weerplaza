import logging
import random
import os
from datetime import datetime, timedelta
import aiohttp
import asyncio
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, BASE_URL, DEBUG_FILE_NAME
from .parser import WeerplazaParser

_LOGGER = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15"
]

class WeerplazaCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config_entry, cache=None, initial_data=None):
        self.config_entry = config_entry
        self.location_path = config_entry.data["location_path"]
        self.cache = cache
        
        # Prime the coordinator with initial data immediately
        self.data = initial_data
        self._last_data = initial_data

        scan_interval = config_entry.options.get("scan_interval", 300)
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"Weerplaza {self.location_path}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self._error_count = 0

    def _save_debug_output(self, text_content):
        path = os.path.join(os.path.dirname(__file__), DEBUG_FILE_NAME)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text_content)
        except Exception as e:
            _LOGGER.error(f"Failed to write debug file: {e}")

    async def _async_update_data(self):
        # Small delay to prevent network congestion on boot
        await asyncio.sleep(random.randint(1, 3))

        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml",
        }

        scrape_url = f"{BASE_URL}{self.location_path.strip('/')}/"

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(scrape_url, timeout=20) as response:
                    if response.status != 200:
                        raise UpdateFailed(f"Server returned {response.status}")

                    html_content = await response.text()
                    self._save_debug_output(html_content)

                    parser = WeerplazaParser(html_content)
                    new_data = parser.extract_data()
                    
                    # Add timestamp
                    new_data["laatste_scrape_tijd"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    
                    # Store locally and save to disk
                    self._last_data = new_data
                    if self.cache:
                        await self.cache.save(new_data)
                    
                    return new_data

        except Exception as err:
            _LOGGER.warning(f"Update failed, using last known data: {err}")
            if self._last_data:
                return self._last_data
            raise UpdateFailed(f"Update error: {err}")
