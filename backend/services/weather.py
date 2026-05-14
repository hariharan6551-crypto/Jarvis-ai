"""
J.A.R.V.I.S Weather Service
OpenWeatherMap integration with Chennai as default location.
Features: current weather, forecast, rain prediction, caching.
"""

import asyncio
import time
from typing import Optional
from core.logger import get_logger
from config.settings import settings

log = get_logger("weather")

# Default location
DEFAULT_CITY = "Chennai"
DEFAULT_COUNTRY = "IN"
DEFAULT_LAT = 13.0827
DEFAULT_LON = 80.2707

# Cache duration (30 minutes)
CACHE_TTL = 1800


class WeatherService:
    """Fetches and caches weather data from OpenWeatherMap."""

    def __init__(self):
        self._api_key = getattr(settings, "OPENWEATHER_API_KEY", None) or ""
        self._cache = {}
        self._cache_time = 0
        self._forecast_cache = {}
        self._forecast_cache_time = 0
        log.info("Weather service initialized")

    async def get_current(self, city: str = DEFAULT_CITY) -> dict:
        """Get current weather for a city."""
        now = time.time()
        cache_key = city.lower()

        # Return cached if fresh
        if cache_key in self._cache and (now - self._cache_time) < CACHE_TTL:
            return self._cache[cache_key]

        try:
            import httpx
            if not self._api_key:
                # Use wttr.in as free fallback (no API key needed)
                return await self._get_wttr(city)

            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                "q": f"{city},{DEFAULT_COUNTRY}" if city == DEFAULT_CITY else city,
                "appid": self._api_key,
                "units": "metric",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    result = self._parse_current(data, city)
                    self._cache[cache_key] = result
                    self._cache_time = now
                    return result
                else:
                    log.warning(f"OpenWeatherMap API error: {resp.status_code}")
                    return await self._get_wttr(city)

        except Exception as e:
            log.error(f"Weather fetch failed: {e}")
            return await self._get_wttr(city)

    async def get_forecast(self, city: str = DEFAULT_CITY, days: int = 5) -> dict:
        """Get weather forecast."""
        now = time.time()
        cache_key = f"{city.lower()}_{days}"

        if cache_key in self._forecast_cache and (now - self._forecast_cache_time) < CACHE_TTL:
            return self._forecast_cache[cache_key]

        try:
            import httpx
            if not self._api_key:
                return {"success": False, "message": "Weather API key not configured"}

            url = "https://api.openweathermap.org/data/2.5/forecast"
            params = {
                "q": f"{city},{DEFAULT_COUNTRY}" if city == DEFAULT_CITY else city,
                "appid": self._api_key,
                "units": "metric",
                "cnt": days * 8,  # 3-hour intervals
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    result = self._parse_forecast(data, city, days)
                    self._forecast_cache[cache_key] = result
                    self._forecast_cache_time = now
                    return result

            return {"success": False, "message": "Forecast unavailable"}

        except Exception as e:
            log.error(f"Forecast fetch failed: {e}")
            return {"success": False, "message": str(e)}

    async def will_it_rain(self, city: str = DEFAULT_CITY) -> dict:
        """Check rain probability for today."""
        weather = await self.get_current(city)
        if not weather.get("success"):
            return {"success": False, "message": "Weather data unavailable"}

        condition = weather.get("condition", "").lower()
        rain_keywords = ["rain", "drizzle", "thunder", "storm", "shower"]
        will_rain = any(k in condition for k in rain_keywords)
        humidity = weather.get("humidity", 0)

        if will_rain:
            message = f"Yes Sir, rain is expected in {city}. Current conditions: {weather['condition']}. Carry an umbrella."
        elif humidity > 80:
            message = f"High humidity at {humidity}% in {city}, Sir. There's a chance of rain later."
        else:
            message = f"No rain expected today in {city}, Sir. Clear skies."

        return {
            "success": True,
            "will_rain": will_rain or humidity > 80,
            "message": message,
            "humidity": humidity,
            "condition": weather.get("condition", ""),
        }

    def get_weather_briefing(self, weather_data: dict) -> str:
        """Generate a spoken weather briefing."""
        if not weather_data.get("success"):
            return "Weather data is currently unavailable, Sir."

        temp = weather_data.get("temp", "N/A")
        condition = weather_data.get("condition", "unknown")
        humidity = weather_data.get("humidity", "N/A")
        city = weather_data.get("city", DEFAULT_CITY)
        feels_like = weather_data.get("feels_like", temp)

        briefing = f"{city} weather: {temp}°C, {condition}."
        if feels_like != temp:
            briefing += f" Feels like {feels_like}°C."
        if humidity and humidity != "N/A":
            briefing += f" Humidity {humidity}%."

        return briefing

    # ─── Parsers ──────────────────────────────────────────────────────

    def _parse_current(self, data: dict, city: str) -> dict:
        """Parse OpenWeatherMap current weather response."""
        main = data.get("main", {})
        weather = data.get("weather", [{}])[0]
        wind = data.get("wind", {})

        return {
            "success": True,
            "city": city,
            "temp": round(main.get("temp", 0)),
            "feels_like": round(main.get("feels_like", 0)),
            "temp_min": round(main.get("temp_min", 0)),
            "temp_max": round(main.get("temp_max", 0)),
            "humidity": main.get("humidity", 0),
            "condition": weather.get("description", "").title(),
            "icon": weather.get("icon", ""),
            "wind_speed": round(wind.get("speed", 0) * 3.6, 1),  # m/s to km/h
            "visibility": data.get("visibility", 10000) / 1000,  # m to km
        }

    def _parse_forecast(self, data: dict, city: str, days: int) -> dict:
        """Parse OpenWeatherMap forecast response."""
        daily = {}
        for item in data.get("list", []):
            date = item["dt_txt"].split(" ")[0]
            if date not in daily:
                daily[date] = {
                    "date": date,
                    "temps": [],
                    "conditions": [],
                }
            daily[date]["temps"].append(item["main"]["temp"])
            daily[date]["conditions"].append(item["weather"][0]["description"])

        forecast_days = []
        for date, info in list(daily.items())[:days]:
            temps = info["temps"]
            forecast_days.append({
                "date": date,
                "temp_min": round(min(temps)),
                "temp_max": round(max(temps)),
                "condition": max(set(info["conditions"]), key=info["conditions"].count).title(),
            })

        return {
            "success": True,
            "city": city,
            "days": forecast_days,
        }

    async def _get_wttr(self, city: str) -> dict:
        """Fallback: use wttr.in (no API key needed)."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"https://wttr.in/{city}?format=j1",
                    headers={"User-Agent": "JARVIS/2.0"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    current = data.get("current_condition", [{}])[0]
                    return {
                        "success": True,
                        "city": city,
                        "temp": int(current.get("temp_C", 0)),
                        "feels_like": int(current.get("FeelsLikeC", 0)),
                        "humidity": int(current.get("humidity", 0)),
                        "condition": current.get("weatherDesc", [{}])[0].get("value", "Unknown"),
                        "wind_speed": int(current.get("windspeedKmph", 0)),
                        "visibility": int(current.get("visibility", 10)),
                        "temp_min": 0,
                        "temp_max": 0,
                        "icon": "",
                    }
        except Exception as e:
            log.error(f"wttr.in fallback failed: {e}")

        return {
            "success": False,
            "city": city,
            "message": "Weather data unavailable",
        }
