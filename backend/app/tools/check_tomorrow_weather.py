import httpx
import urllib.parse
from datetime import datetime

def check_tomorrow_weather(params: dict) -> dict:
    """
    查询明天的天气情况。
    如果参数中没有指定城市，则通过IP地址自动检测当前位置，
    然后查询该位置明天的天气信息。
    """
    try:
        # 检查是否提供了城市参数
        if 'city' in params and params['city']:
            city = params['city']
        else:
            # 如果没有提供城市，则通过IP获取当前城市
            ip_response = httpx.get("http://ip-api.com/json/?lang=zh-CN", timeout=10)
            ip_data = ip_response.json()
            if ip_data.get("status") == "success":
                city = ip_data.get("city")
            else:
                return {"success": False, "result": "无法获取当前位置信息"}

        # 对城市名进行URL编码以处理中文字符
        encoded_city = urllib.parse.quote(city)

        # 查询天气信息
        weather_url = f"https://wttr.in/{encoded_city}?format=j1&lang=zh"
        weather_response = httpx.get(weather_url, timeout=15)
        
        if weather_response.status_code != 200:
            return {"success": False, "result": f"天气查询失败，状态码: {weather_response.status_code}"}

        weather_data = weather_response.json()

        # 提取明天的天气数据
        if "weather" in weather_data and len(weather_data["weather"]) > 1:
            tomorrow_weather = weather_data["weather"][1]  # 第一个元素是今天，第二个是明天
            
            result = {
                "location": city,
                "date": tomorrow_weather.get("date", ""),
                "temperature_min": tomorrow_weather["mintempC"] + "°C",
                "temperature_max": tomorrow_weather["maxtempC"] + "°C",
                "weather_condition": tomorrow_weather["hourly"][0]["weatherDesc"][0]["value"],
                "humidity": tomorrow_weather["hourly"][0]["humidity"] + "%",
                "wind_speed": tomorrow_weather["hourly"][0]["windspeedKmph"] + " km/h"
            }
            
            return {"success": True, "result": result}
        else:
            return {"success": False, "result": "未能获取到明天的天气数据"}
    
    except httpx.TimeoutException:
        return {"success": False, "result": "请求超时"}
    except Exception as e:
        return {"success": False, "result": f"发生错误: {str(e)}"}