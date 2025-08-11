"""API Client for scraping Weerplaza.nl data."""
import asyncio
import logging
import socket
from datetime import datetime
from typing import Any, Dict, List, Optional

import async_timeout
from aiohttp import ClientError, ClientSession
from bs4 import BeautifulSoup

from .const import BASE_URL, API_TIMEOUT

_LOGGER = logging.getLogger(__name__)

class WeerplazaApiClientError(Exception):
    """Generic Weerplaza API Error."""

class WeerplazaApiConnectionError(WeerplazaApiClientError):
    """Weerplaza API Connection Error."""

class WeerplazaApiParsingError(WeerplazaApiClientError):
    """Weerplaza API Parsing Error (e.g., website structure changed)."""

class WeerplazaApiNoDataError(WeerplazaApiClientError):
    """Weerplaza API No Data Error (e.g., invalid location path or no messages)."""


class WeerplazaApiClient:
    """Weerplaza API Client."""

    def __init__(self, session: ClientSession):
        """Initialize the API client."""
        self._session = session
        self._base_url = BASE_URL

    async def async_scrape_data(self, location_path: str) -> Dict[str, Any] | None:
        """Fetch and parse Weerplaza data for a given location path."""
        url = f"{self._base_url}{location_path.strip('/')}/" # Ensure trailing slash
        _LOGGER.debug("Requesting Weerplaza data from: %s", url)
        headers = {"User-Agent": "HomeAssistant Weerplaza Integration"} # Be a good citizen

        try:
            async with async_timeout.timeout(API_TIMEOUT):
                response = await self._session.get(url, headers=headers)
                # Allow 404 as it might mean an invalid location path
                if response.status == 404:
                    _LOGGER.warning("Received 404 for %s, likely invalid location path.", url)
                    raise WeerplazaApiNoDataError(f"Invalid location path (404): {location_path}")
                response.raise_for_status() # Raise HTTPError for other bad responses (e.g., 5xx)
                html_content = await response.text()

        except asyncio.TimeoutError as exc:
            _LOGGER.error("Timeout occurred while requesting Weerplaza data for %s", location_path)
            raise WeerplazaApiConnectionError(f"Timeout connecting to {url}") from exc
        except (ClientError, socket.gaierror) as exc:
            _LOGGER.error("Communication error occurred while requesting Weerplaza data for %s: %s", location_path, exc)
            raise WeerplazaApiConnectionError(f"Communication error with {url}") from exc

        _LOGGER.debug("Parsing HTML content from %s", url)
        try:
            soup = BeautifulSoup(html_content, 'lxml') # Use lxml for speed
            scraped_data = {}

            # --- 1. Extract Warnings (Waarschuwingen) ---
            warnings_section = soup.find('h2', string='Waarschuwingen')
            if warnings_section:
                warning_box = warnings_section.find_next_sibling('div').find('div', class_='border')
                if warning_box:
                    warning_code_element = warning_box.find('h3', class_='h3')
                    warning_text_element = warning_box.find('p', class_='font-normal')
                    warning_link_element = warning_box.find('a', class_='button-link')

                    warning_code = warning_code_element.get_text(strip=True) if warning_code_element else None
                    warning_text = warning_text_element.get_text(strip=True) if warning_text_element else None
                    warning_link = warning_link_element['href'] if warning_link_element else None

                    scraped_data["warnings"] = {
                        "code": warning_code,
                        "description": warning_text,
                        "link": f"{self._base_url.rstrip('/')}{warning_link}" if warning_link else None
                    }
                else:
                    scraped_data["warnings"] = None # No active warning box found
            else:
                scraped_data["warnings"] = None # No warnings section found

            # --- 2. Extract Flash Message ---
            flash_banner = soup.find('div', class_='rounded-md border', style=lambda value: value and 'yellow' in value)
            if flash_banner:
                flash_title_element = flash_banner.find('div', class_='flex items-center')
                flash_message_element = flash_banner.find('p', class_='text-xs')

                flash_title = flash_title_element.get_text(strip=True).replace('Flash', '').strip() if flash_title_element else "Flash"
                flash_message = flash_message_element.get_text(strip=True) if flash_message_element else None

                scraped_data["flash_message"] = {
                    "title": flash_title,
                    "message": flash_message
                }
            else:
                scraped_data["flash_message"] = None # No flash message banner found

            # --- 3. Extract Hourly Forecast ---
            hourly_forecast_items = []
            hourly_forecast_section = soup.find('h2', string='Weerbericht uur tot uur')
            if hourly_forecast_section:
                hourly_container = hourly_forecast_section.find_next_sibling('div')
                if hourly_container:
                    for item_div in hourly_container.find_all('div', class_='flex flex-col items-center'):
                        time_element = item_div.find('p', class_='text-sm')
                        img_element = item_div.find('img')
                        temp_element = item_div.find('p', class_='text-xl')
                        precip_element = item_div.find('div', class_='flex items-center')

                        time = time_element.get_text(strip=True) if time_element else None
                        description = img_element['alt'] if img_element and 'alt' in img_element.attrs else None
                        temperature = temp_element.get_text(strip=True) if temp_element else None
                        precipitation = precip_element.find('span').get_text(strip=True) if precip_element and precip_element.find('span') else None

                        hourly_forecast_items.append({
                            'time': time,
                            'description': description,
                            'temperature': temperature,
                            'precipitation': precipitation
                        })
            scraped_data["hourly_forecast"] = hourly_forecast_items

            # --- 4. Extract Daily Forecast ---
            daily_forecast_items = []
            daily_forecast_section = soup.find('h2', string='Weerbericht daaglijks')
            if daily_forecast_section:
                daily_container = daily_forecast_section.find_next_sibling('div')
                if daily_container:
                    for day_div in daily_container.find_all('div', class_='bg-gray-50'):
                        day_title_element = day_div.find('h3', class_='h3')
                        day_title = day_title_element.get_text(strip=True) if day_title_element else None
                        
                        day_parts = []
                        for part_div in day_div.find_all('div', class_='flex flex-col items-center'):
                            time_of_day_element = part_div.find('p', class_='text-sm')
                            img_element = part_div.find('img')
                            temp_element = part_div.find('p', class_='text-xl')
                            precip_element = part_div.find('div', class_='flex items-center')

                            time_of_day = time_of_day_element.get_text(strip=True) if time_of_day_element else None
                            description = img_element['alt'] if img_element and 'alt' in img_element.attrs else None
                            temperature = temp_element.get_text(strip=True) if temp_element else None
                            precipitation = precip_element.find('span').get_text(strip=True) if precip_element and precip_element.find('span') else None
                            
                            day_parts.append({
                                'time_of_day': time_of_day,
                                'description': description,
                                'temperature': temperature,
                                'precipitation': precipitation
                            })
                        daily_forecast_items.append({'day': day_title, 'parts': day_parts})
            scraped_data["daily_forecast"] = daily_forecast_items

            # --- 5. Extract Current Temperature (from first hourly forecast item if available) ---
            scraped_data["current_temperature"] = None
            if scraped_data["hourly_forecast"] and scraped_data["hourly_forecast"][0].get('temperature'):
                scraped_data["current_temperature"] = scraped_data["hourly_forecast"][0]['temperature']

            _LOGGER.debug("Successfully parsed data for %s: %s", location_path, scraped_data)
            return scraped_data

        except Exception as exc:
            _LOGGER.exception("Error parsing Weerplaza data for %s: %s", location_path, exc)
            raise WeerplazaApiParsingError(f"Failed to parse HTML from {url}") from exc
