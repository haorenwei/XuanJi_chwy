import httpx
import urllib.parse
from typing import Dict

def get_weather_info(params: dict) -> dict:
    """
    获取无锡明天的天气信息
    如果没有指定城市，则通过IP定位获取当前位置，然后查询天气
    """
    try:
        # 首先尝试获取用户位置（如果未指定城市）
        city = "无锡"
        
        # 对城市名进行URL编码以处理中文字符
        encoded_city = urllib.parse.quote(city)
        
        # 查询天气信息，使用format=j1获取JSON格式数据
        weather_url = f"https://wttr.in/{encoded_city}?format=j1&lang=zh"
        resp = httpx.get(weather_url, timeout=15)
        
        if resp.status_code == 200:
            weather_data = resp.json()
            
            # 提取明天的天气信息
            if 'weather' in weather_data and len(weather_data['weather']) > 1:
                tomorrow_weather = weather_data['weather'][1]  # 第二天即明天
                
                # 获取白天天气描述
                day_condition = tomorrow_weather['hourly'][0]['weatherDesc'][0]['value']
                
                # 获取温度范围
                min_temp = tomorrow_weather['mintempC']
                max_temp = tomorrow_weather['maxtempC']
                
                # 获取其他信息
                date = tomorrow_weather['date']
                
                result = {
                    "city": city,
                    "date": date,
                    "condition": day_condition,
                    "min_temp": f"{min_temp}°C",
                    "max_temp": f"{max_temp}°C",
                    "detailed_info": tomorrow_weather
                }
                
                return {"success": True, "result": result}
            else:
                return {"success": False, "result": "无法获取明天的天气信息"}
        else:
            return {"success": False, "result": f"天气查询失败，状态码: {resp.status_code}"}
    
    except httpx.TimeoutException:
        return {"success": False, "result": "请求超时"}
    except Exception as e:
        return {"success": False, "result": f"发生错误: {str(e)}"}