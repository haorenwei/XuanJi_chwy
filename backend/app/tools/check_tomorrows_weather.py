import httpx
import urllib.parse
from datetime import datetime, timedelta


def check_tomorrows_weather(params: dict) -> dict:
    """
    Check tomorrow's weather by first detecting the user's location based on their IP,
    then fetching weather forecast for tomorrow from wttr.in service.
    
    Args:
        params: A dictionary containing date information (should have 'date' key with value 'tomorrow')
        
    Returns:
        A dictionary with success status and weather information
    """
    try:
        # Detect location based on IP
        location_resp = httpx.get("http://ip-api.com/json/?lang=zh-CN", timeout=10)
        if location_resp.status_code != 200:
            return {"success": False, "result": "Failed to detect location"}
        
        location_data = location_resp.json()
        city = location_data.get("city")
        
        if not city:
            return {"success": False, "result": "Could not determine city from IP"}
        
        # URL encode the city name in case it contains non-ASCII characters
        encoded_city = urllib.parse.quote(city)
        
        # Get weather data for the detected city
        weather_url = f"https://wttr.in/{encoded_city}?format=j1&lang=zh"
        weather_resp = httpx.get(weather_url, timeout=15)
        
        if weather_resp.status_code != 200:
            return {"success": False, "result": f"Weather service returned status {weather_resp.status_code}"}
        
        weather_data = weather_resp.json()
        
        # Extract tomorrow's weather information
        if "weather" in weather_data and len(weather_data["weather"]) > 1:
            # The first entry is today, the second is tomorrow
            tomorrow_weather = weather_data["weather"][1]
            
            # Format the result
            result = {
                "location": city,
                "date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                "condition": tomorrow_weather.get("hourly", [{}])[0].get("weatherDesc", [{}])[0].get("value", "Unknown"),
                "temperature": tomorrow_weather.get("hourly", [{}])[0].get("tempC", "Unknown"),
                "humidity": tomorrow_weather.get("hourly", [{}])[0].get("humidity", "Unknown"),
                "wind_speed": tomorrow_weather.get("hourly", [{}])[0].get("windspeedKmph", "Unknown"),
            }
            
            return {"success": True, "result": result}
        else:
            return {"success": False, "result": "Could not retrieve tomorrow's weather data"}
    
    except httpx.TimeoutException:
        return {"success": False, "result": "Request timed out while fetching weather data"}
    
    except httpx.RequestError as e:
        return {"success": False, "result": f"Request error occurred: {str(e)}"}
    
    except Exception as e:
        return {"success": False, "result": f"An unexpected error occurred: {str(e)}"}