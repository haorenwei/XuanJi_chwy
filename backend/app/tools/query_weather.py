import httpx
import urllib.parse
from typing import Dict, Any

def query_weather(params: dict) -> dict:
    """
    查询指定城市或当前IP所在城市的天气信息。
    如果未提供城市参数，则自动检测IP所在地的城市并查询天气。
    返回包含温度、湿度、风速等天气信息的字典。
    """
    try:
        # 获取城市名称，如果未提供则通过IP获取当前位置
        city = params.get('city', None)
        
        if not city:
            # 通过IP获取当前位置
            ip_response = httpx.get("http://ip-api.com/json/?lang=zh-CN", timeout=10)
            ip_data = ip_response.json()
            
            if ip_data.get("status") == "success":
                city = ip_data.get("city")
                if not city:
                    return {"success": False, "result": "无法通过IP获取城市信息"}
            else:
                return {"success": False, "result": "IP定位失败"}
        
        # 对非ASCII字符进行URL编码
        encoded_city = urllib.parse.quote(city)
        
        # 查询天气信息
        weather_url = f"https://wttr.in/{encoded_city}?format=j1&lang=zh"
        weather_response = httpx.get(weather_url, timeout=15)
        
        if weather_response.status_code != 200:
            return {"success": False, "result": f"天气查询失败，状态码: {weather_response.status_code}"}
        
        weather_data = weather_response.json()
        
        # 解析天气数据
        current_condition = weather_data["current_condition"][0]
        weather_description = current_condition["weatherDesc"][0]["value"]
        temperature = current_condition["temp_C"]
        humidity = current_condition["humidity"]
        wind_speed = current_condition["windspeedKmph"]
        feels_like = current_condition["FeelsLikeC"]
        
        result = {
            "location": city,
            "description": weather_description,
            "temperature": f"{temperature}°C",
            "feels_like": f"{feels_like}°C",
            "humidity": f"{humidity}%",
            "wind_speed": f"{wind_speed} km/h",
            "raw_data": weather_data
        }
        
        return {"success": True, "result": result}
    
    except httpx.TimeoutException:
        return {"success": False, "result": "请求超时"}
    except httpx.RequestError as e:
        return {"success": False, "result": f"网络请求错误: {str(e)}"}
    except KeyError as e:
        return {"success": False, "result": f"解析天气数据时出错: {str(e)}"}
    except Exception as e:
        return {"success": False, "result": f"查询天气时发生未知错误: {str(e)}"}