import httpx
import urllib.parse

def get_weather_today(params: dict) -> dict:
    """
    Query today's weather information for the current location based on IP geolocation.
    Returns weather details including temperature, condition, wind speed, and humidity.
    """
    try:
        # First, get the current location based on IP
        location_response = httpx.get("http://ip-api.com/json/?lang=zh-CN", timeout=10)
        location_data = location_response.json()
        
        if location_response.status_code != 200 or location_data.get("status") != "success":
            return {"success": False, "result": "无法获取当前位置信息"}
        
        city = location_data.get("city", "")
        if not city:
            return {"success": False, "result": "未能获取到城市信息"}
        
        # URL encode the city name to handle non-ASCII characters
        encoded_city = urllib.parse.quote(city)
        
        # Get weather information for the city
        weather_response = httpx.get(f"https://wttr.in/{encoded_city}?format=j1&lang=zh", timeout=15)
        
        if weather_response.status_code != 200:
            return {"success": False, "result": f"天气查询失败，状态码: {weather_response.status_code}"}
        
        weather_data = weather_response.json()
        
        # Extract current weather information
        current_weather = weather_data.get("current_condition", [{}])[0]
        
        result = {
            "location": city,
            "temperature": current_weather.get("temp_C", "N/A") + "°C",
            "description": current_weather.get("weatherDesc", [{}])[0].get("value", "N/A"),
            "wind_speed": current_weather.get("windspeedKmph", "N/A") + " km/h",
            "humidity": current_weather.get("humidity", "N/A") + "%",
            "feels_like": current_weather.get("FeelsLikeC", "N/A") + "°C"
        }
        
        return {"success": True, "result": result}
    
    except httpx.TimeoutException:
        return {"success": False, "result": "请求超时，请稍后重试"}
    except httpx.RequestError as e:
        return {"success": False, "result": f"网络请求错误: {str(e)}"}
    except Exception as e:
        return {"success": False, "result": f"发生未知错误: {str(e)}"}