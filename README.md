# Weerplaza Weather Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)][hacs]
[![Project Maintenance][maintenance_badge]](https://github.com/Malosaaa/ha-weerplaza)

This custom component for Home Assistant allows you to monitor weather data for any location from the Dutch weather site [Weerplaza.nl](https://www.weerplaza.nl/). It works by scraping the data directly from the location's page, providing detailed weather information without requiring an official API.

> **Disclaimer:** This integration relies on web scraping. If Weerplaza.nl changes the HTML structure of its website, this integration will likely break until it is updated. Please be a good citizen and use a reasonable update interval to avoid overloading their servers.

This integration was created with significant collaboration, testing, and debugging from **TranQuiL (@Malosaaa)**.

***
## Features

*   ✅ **Easy UI-Based Setup**: Configure entirely through the Home Assistant user interface. No YAML required for setup.
*   ✅ **Supports Any Location**: Simply find your location's path on Weerplaza.nl (e.g., `nederland/utrecht/19344/`) and use it during setup.
*   ✅ **Multi-Sensor Data**: Scrapes current temperature, weather warnings, flash messages, and detailed hourly & daily forecasts.
*   ✅ **Device Grouping**: Creates a single Home Assistant Device for your location, with all related sensors neatly attached to it.
*   ✅ **Configurable Updates**: Easily change the data refresh interval through the integration's options.
*   ✅ **Robust Error Handling**: If an update fails, the integration keeps the last successful data to prevent sensors from becoming `unavailable`.
*   ✅ **Diagnostic Sensors**: Includes disabled-by-default sensors to monitor the health and status of the integration.

## Installation

### Method 1: HACS (Home Assistant Community Store) - Recommended

1.  Ensure you have [HACS](https://hacs.xyz/) installed.
2.  Go to HACS -> Integrations -> Click the 3-dots menu in the top right -> **Custom Repositories**.
3.  In the "Repository" field, paste this URL: `https://github.com/Malosaa/ha-weerplaza`
4.  For "Category", select **Integration**.
5.  Click **Add**.
6.  The "Weerplaza Weather" integration will now appear in your HACS integrations list. Click **Install** or **Download**.
7.  Restart Home Assistant.

### Method 2: Manual Installation

1.  Using a file access tool (like Samba or File Editor), navigate to the `custom_components` directory in your Home Assistant `config` folder.
2.  Create a new folder named `weerplaza`.
3.  Copy all the files from this repository's `weerplaza` directory (`__init__.py`, `manifest.json`, `sensor.py`, etc.) into the new `weerplaza` folder.
4.  Restart Home Assistant.

## Configuration

After installing and restarting, you can add your Weerplaza location.

1.  Navigate to **Settings** -> **Devices & Services**.
2.  Click the **+ ADD INTEGRATION** button in the bottom right.
3.  Search for "**Weerplaza Weather**" and select it.
4.  You will be prompted for two items:
    *   **Friendly Name**: A unique name for this location, e.g., `Utrecht Weather`. This will be used for your device and entities.
    *   **Location Path**: The path from the Weerplaza URL. Find your city on Weerplaza.nl and copy the part of the URL *after* `.nl/`. For `https://www.weerplaza.nl/nederland/utrecht/19344/`, the path is `nederland/utrecht/19344/`.
5.  Enter the details and click **Submit**.
6.  The integration will be set up, creating a new device and its associated sensors.

## Dashboard Card Setup

### 1. Icon Setup (Required for the Example Card)

The example dashboard card uses custom icons to display the weather conditions. You need to place these icons in the correct folder.

1.  In your Home Assistant `config` directory, find the `www` folder. If it does not exist, create it.
2.  Inside the `www` folder, create a new folder named `weerplaza-icons`.
3.  The final path should look like this: `config/www/weerplaza-icons/`.
4.  Place your desired weather icon files (e.g., `.png` or `.svg` files) inside this `weerplaza-icons` folder.
5.  Home Assistant makes this directory available at the URL `/local/weerplaza-icons/`, which the dashboard card uses to find the icons.

### 2. Dashboard Card Installation

The file `dashboard-card.txt` contains the code for a nice-looking dashboard card.

**Prerequisite:** This card requires the **[Mushroom Cards](https://github.com/piitaya/lovelace-mushroom)** integration. Please install it from HACS before proceeding.

1.  In your Home Assistant dashboard, click the three dots (⋮) in the top-right corner and select **Edit Dashboard**.
2.  Click the **+ Add Card** button and choose the **Manual** card from the bottom of the list.
3.  Open the `dashboard-card.txt` file.
4.  Copy the **entire content** of the file and paste it into the Manual card's code editor.
5.  **Crucially, you must replace every instance of `YOURPLACE` with the slug of your instance name.** For example, if your main sensor is `sensor.weerplaza_YOURPLACE_weather_current_weather`, your slug is `YOURPLACE_weather`.

> ### **Very Important Note on the Example Card**
> The code in `dashboard-card.txt` is an advanced example and references several data attributes (like `astro`, `moon_phases`, `daily_forecast_summary`, and specific `icon` fields).

*Remember to replace `YOURPLACE` in the dashboard-card.txt with your own instance slug!*

## Sensors Provided

The integration creates the following sensors. The `<instance_slug>` is derived from the friendly name you provided (e.g., `utrecht_weather`).
Also it contains all other data like ASTRO-MOONPHASES-LIGHTNING etc as attributes.

| Sensor Name | Example Entity ID | Description |
| :--- | :--- | :--- |
| **Current Weather** | `sensor.weerplaza_<instance_slug>_current_weather` | Main sensor. State is the current temperature in °C. Attributes contain all other scraped data (`warnings`, `hourly_forecast`, etc.). |
| **Warnings** | `sensor.weerplaza_<instance_slug>_warnings` | The current weather warning code (e.g., "Code Geel") or "Geen waarschuwing". |
| **Flash Message** | `sensor.weerplaza_<instance_slug>_flash_message` | Displays special alert messages from Weerplaza. |
| **Hourly Forecast** | `sensor.weerplaza_<instance_slug>_hourly_forecast` | State is the number of forecast hours available. Attributes contain the full forecast list. |
| **Daily Forecast** | `sensor.weerplaza_<instance_slug>_daily_forecast` | State is the number of forecast days available. Attributes contain the full forecast list. |
| **Last Update Status** | `sensor.weerplaza_<instance_slug>_diag_last_update_status` | (Disabled) Shows "OK" or "Error". |
| **Last Update Time** | `sensor.weerplaza_<instance_slug>_diag_last_update_time` | (Disabled) Timestamp of the last successful update. |
| **Consecutive Errors** | `sensor.weerplaza_<instance_slug>_diag_consecutive_errors` | (Disabled) Counts successive update failures. |


[hacs]: https://hacs.xyz
[hacs_badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge
[maintenance_badge]: https://img.shields.io/badge/Maintained%3F-yes-green.svg?style=for-the-badge
