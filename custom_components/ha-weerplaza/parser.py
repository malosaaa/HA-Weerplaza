from bs4 import BeautifulSoup
import re
import logging

_LOGGER = logging.getLogger(__name__)

class WeerplazaParser:
    def __init__(self, html):
        self.soup = BeautifulSoup(html, "lxml")
        for element in self.soup(["script", "style", "noscript", "meta"]):
            element.extract()

    def extract_data(self):
        scraped_data = {
            "current_weather": {},
            "hourly_forecast": [],
            "daily_forecast_summary": [],
            "daypart_forecast": [],
            "flash_message": {"message": "Geen weeralarm"},
            "flash_detection": "Geen bliksem",
            "flash_range": None,
            "rain": "Onbekend",
            "alerts": "Er zijn nu geen waarschuwingen",
            "astro": {"sun": {"rise": "-", "set": "-"}},
            "moon_phases": [],
            "current_temperature": None
        }

        # 1. FLASH + SPLASH + ALERTS
        try:
            alerts_list = []
            splash = self.soup.find("a", class_=re.compile("btn-splash"))
            if splash:
                s_text = splash.find("span", class_="text")
                if s_text:
                    scraped_data["rain"] = s_text.get_text(strip=True)
                    alerts_list.append(f"Regen: {scraped_data['rain']}")

            flash = self.soup.find("a", class_=re.compile("btn-flash"))
            if flash:
                f_text = flash.find("span", class_="text")
                if f_text:
                    detect_text = f_text.get_text(strip=True)
                    scraped_data["flash_detection"] = detect_text
                    range_match = re.search(r"(\d+)", detect_text)
                    if range_match:
                        scraped_data["flash_range"] = int(range_match.group(1))
                    alerts_list.append(f"Onweer: {detect_text}")

            warning_block = self.soup.find("div", class_="meteo-warning-block")
            if warning_block:
                w_text = warning_block.find("span", class_="text")
                if w_text:
                    scraped_data["alerts"] = w_text.get_text(strip=True)

            if alerts_list:
                scraped_data["flash_message"] = {"message": " | ".join(alerts_list)}
        except Exception:
            pass

        # 2. ASTRO (SUN & MOON)
        try:
            astro_block = self.soup.find("div", class_=re.compile("forecast-astro"))
            if astro_block:
                for label, key in [("Zon op", "rise"), ("Zon onder", "set")]:
                    tag = astro_block.find("b", string=re.compile(label, re.I))
                    if tag and tag.parent:
                        full_text = tag.parent.get_text(separator=" ", strip=True)
                        match = re.search(r"(\d{2}:\d{2})", full_text)
                        if match:
                            scraped_data["astro"]["sun"][key] = match.group(1)

                phases = ["Eerste kwartier", "Volle maan", "Laatste kwartier", "Nieuwe maan"]
                for p_name in phases:
                    p_tag = astro_block.find(string=re.compile(p_name, re.I))
                    if p_tag:
                        container = p_tag.find_parent("div", class_="col") or p_tag.parent
                        img = container.find("img")
                        full_text = container.get_text(separator=" ", strip=True)
                        date_val = full_text.replace(p_name, "").strip()
                        icon_path = img.get("src") if img else ""
                        if icon_path and icon_path.startswith("/"):
                            icon_path = f"https://www.weerplaza.nl{icon_path}"
                        scraped_data["moon_phases"].append({
                            "phase": p_name, "datetime": date_val, "icon": icon_path
                        })
        except Exception:
            pass

        # 3. HOURLY FORECAST
        try:
            hourly_container = self.soup.find("div", id="hourly")
            if hourly_container:
                for hour_div in hourly_container.find_all("div", class_="hour"):
                    head = hour_div.find("div", class_=re.compile("head"))
                    time_val = head.find_all("div")[-1].get_text(strip=True) if head else "--:--"
                    wx_div = hour_div.find("div", class_="wx")
                    icon_match = re.search(r"url\(['\"]?(.*?)['\"]?\)", wx_div.get("style", "")) if wx_div else None
                    temp_div = hour_div.find("div", class_=re.compile("temp"))
                    temp_str = temp_div.get_text(strip=True).replace("\u00b0C", "") if temp_div else None
                    scraped_data["hourly_forecast"].append({
                        "time": time_val,
                        "temperature": float(temp_str) if temp_str else "-",
                        "icon": icon_match.group(1) if icon_match else ""
                    })
        except Exception:
            pass

        # 4. DAILY FORECAST SUMMARY (MATCHING BY DATA-DAY)
        try:
            daily_section = self.soup.find("div", id="fullday")
            if daily_section:
                day_map = {}
                # Extract all unique data-day values to preserve order
                all_cells = daily_section.find_all("td", attrs={"data-day": True})
                
                for cell in all_cells:
                    day_id = cell["data-day"]
                    if day_id not in day_map:
                        day_map[day_id] = {
                            "date_short": "-",
                            "description_icon_title": "-",
                            "temp_high": "-",
                            "temp_low": "-",
                            "icon": ""
                        }
                    
                    # 4a. Get Day Name & Date
                    head = cell.find("div", class_="show-large") or cell.find("div", class_="hide-large")
                    if head:
                        day_name = head.find(string=True, recursive=False)
                        day_name = day_name.strip() if day_name else ""
                        date_div = head.find("div")
                        date_txt = date_div.get_text(strip=True) if date_div else ""
                        day_map[day_id]["date_short"] = f"{day_name} {date_txt}".strip().capitalize()

                    # 4b. Get Icon & Description
                    wx = cell.find("div", class_="wx")
                    if wx:
                        icon_match = re.search(r"url\(['\"]?(.*?)['\"]?\)", wx.get("style", ""))
                        day_map[day_id]["icon"] = icon_match.group(1) if icon_match else ""
                        day_map[day_id]["description_icon_title"] = wx.get("title", "Verwachting")

                    # 4c. Get Temperatures (Red = Max, Blue = Min)
                    # We replace the degree symbol safely using Unicode \u00b0
                    red_temp = cell.find("div", class_="red temp")
                    if red_temp:
                        day_map[day_id]["temp_high"] = red_temp.get_text(strip=True).replace("\u00b0C", "").replace("\u00b0", "").strip()
                    
                    blue_temp = cell.find("div", class_="blue temp")
                    if blue_temp:
                        day_map[day_id]["temp_low"] = blue_temp.get_text(strip=True).replace("\u00b0C", "").replace("\u00b0", "").strip()

                # Convert map back to list in original order
                seen_ids = []
                for cell in all_cells:
                    d_id = cell["data-day"]
                    if d_id not in seen_ids:
                        scraped_data["daily_forecast_summary"].append(day_map[d_id])
                        seen_ids.append(d_id)
        except Exception as e:
            _LOGGER.debug(f"Daily parsing error: {e}")

        # Padding for UI
        while len(scraped_data["daily_forecast_summary"]) < 4:
            scraped_data["daily_forecast_summary"].append({"date_short": "-", "description_icon_title": "-", "temp_high": "-", "temp_low": "-", "icon": ""})

        # 5. CURRENT WEATHER
        try:
            widget = self.soup.find("div", class_=re.compile("location-widget"))
            if widget:
                wx = widget.find("div", class_=re.compile("wx"))
                temp_span = widget.find("span", class_="temp")
                temp_val = float(temp_span.get_text(strip=True).replace("\u00b0", "")) if temp_span else None
                icon_m = re.search(r"url\(['\"]?(.*?)['\"]?\)", wx.get("style", "")) if wx else None
                scraped_data["current_weather"] = {
                    "description_icon_title": wx.get("title", "Onbekend") if wx else "Onbekend",
                    "temperature": temp_val,
                    "location_name_observed": widget.find("h2").get_text(strip=True).replace("Het weer nu in ", "") if widget.find("h2") else "Weerplaza",
                    "icon": icon_m.group(1) if icon_m else ""
                }
                scraped_data["current_temperature"] = temp_val
        except Exception:
            pass

        # 6. DAYPART FORECAST
        h = scraped_data["hourly_forecast"]
        if len(h) >= 13:
            scraped_data["daypart_forecast"] = [
                {"time_of_day": "Ochtend", "temperature": h[0]["temperature"], "icon": h[0]["icon"]},
                {"time_of_day": "Middag", "temperature": h[4]["temperature"], "icon": h[4]["icon"]},
                {"time_of_day": "Avond", "temperature": h[8]["temperature"], "icon": h[8]["icon"]},
                {"time_of_day": "Nacht", "temperature": h[12]["temperature"], "icon": h[12]["icon"]},
            ]

        return scraped_data
