import httpx
import urllib.parse
from typing import Dict

def get_weather_forecast(params: dict) -> dict:
    """
    获取明天的天气预报信息。
    如果没有指定城市，则通过IP地址自动检测当前位置，然后查询该城市的天气预报。
    返回包含成功状态和天气数据的字典。
    """
    try:
        # 首先获取当前城市位置（如果没有提供城市参数）
        resp = httpx.get("http://ip-api.com/json/?lang=zh-CN", timeout=10)
        if resp.status_code != 200:
            return {"success": False, "result": "无法获取当前位置信息"}
        
        location_data = resp.json()
        city = location_data.get("city")
        
        if not city:
            return {"success": False, "result": "无法确定所在城市"}
        
        # 对城市名进行URL编码以处理中文字符
        encoded_city = urllib.parse.quote(city)
        
        # 查询天气信息
        weather_url = f"https://wttr.in/{encoded_city}?format=j1&lang=zh"
        weather_resp = httpx.get(weather_url, timeout=15)
        
        if weather_resp.status_code != 200:
            return {"success": False, "result": f"无法获取{city}的天气信息"}
        
        weather_data = weather_resp.json()
        
        # 提取明天的天气信息
        if 'weather' in weather_data and len(weather_data['weather']) > 1:
            tomorrow_weather = weather_data['weather'][1]  # 第一个元素是今天，第二个是明天
            result = {
                "location": city,
                "date": tomorrow_weather.get("date", "未知"),
                "weather_desc": tomorrow_weather["hourly"][0].get("weatherDesc", [{}])[0].get("value", "未知") if tomorrow_weather["hourly"] else "未知",
                "temp_max_c": tomorrow_weather.get("maxtempC", "未知"),
                "temp_min_c": tomorrow_weather.get("mintempC", "未知"),
                "temp_max_f": tomorrow_weather.get("maxtempF", "未知"),
                "temp_min_f": tomorrow_weather.get("mintempF", "未知"),
            }
            return {"success": True, "result": result}
        else:
            return {"success": False, "result": "天气数据格式异常或无明日预报"}
    
    except httpx.TimeoutException:
        return {"success": False, "result": "请求超时"}
    except Exception as e:
        return {"success": False, "result": f"发生错误: {str(e)}"}