import httpx
import urllib.parse
from datetime import datetime

def get_tomorrow_weather(params: dict) -> dict:
    """
    Query tomorrow's weather forecast for the user's current location.
    First detects the user's city using IP geolocation, then fetches weather data.
    Returns weather information including temperature, conditions, and other details.
    """
    try:
        # Detect user's location based on IP
        location_resp = httpx.get("http://ip-api.com/json/?lang=zh-CN", timeout=10)
        location_data = location_resp.json()
        
        if location_resp.status_code != 200 or location_data.get("status") != "success":
            return {"success": False, "result": "无法获取当前位置信息"}
        
        city = location_data.get("city")
        if not city:
            return {"success": False, "result": "未能识别城市信息"}
        
        # Encode city name for URL
        encoded_city = urllib.parse.quote(city)
        
        # Get weather data
        weather_url = f"https://wttr.in/{encoded_city}?format=j1&lang=zh"
        weather_resp = httpx.get(weather_url, timeout=15)
        
        if weather_resp.status_code != 200:
            return {"success": False, "result": f"天气查询失败，状态码: {weather_resp.status_code}"}
        
        weather_data = weather_resp.json()
        
        # Extract tomorrow's weather info
        if "weather" in weather_data and len(weather_data["weather"]) > 1:
            tomorrow_weather = weather_data["weather"][1]  # Index 1 is tomorrow
            avg_temp_c = tomorrow_weather.get("avgtempC", "N/A")
            condition = tomorrow_weather.get("hourly", [{}])[0].get("weatherDesc", [{}])[0].get("value", "未知")
            
            result = {
                "location": city,
                "date": tomorrow_weather.get("date", "未知"),
                "condition": condition,
                "avg_temperature": f"{avg_temp_c}°C",
                "max_temp": f"{tomorrow_weather.get('maxtempC', 'N/A')}°C",
                "min_temp": f"{tomorrow_weather.get('mintempC', 'N/A')}°C",
                "humidity": f"{tomorrow_weather.get('hourly', [{}])[0].get('humidity', 'N/A')}%",
                "wind_speed": f"{tomorrow_weather.get('hourly', [{}])[0].get('windspeedKmph', 'N/A')} km/h"
            }
            
            return {"success": True, "result": result}
        else:
            return {"success": False, "result": "未能获取明天的天气数据"}
    
    except httpx.TimeoutException:
        return {"success": False, "result": "请求超时，请稍后重试"}
    except Exception as e:
        return {"success": False, "result": f"发生错误: {str(e)}"}