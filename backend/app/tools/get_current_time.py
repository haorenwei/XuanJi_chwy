from datetime import datetime

def get_current_time(params: dict) -> dict:
    """
    获取当前最新时间
    
    Args:
        params: 空字典，不需要任何参数
    
    Returns:
        dict: 包含成功状态和当前时间字符串的结果
    """
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return {"success": True, "result": current_time}
    except Exception as e:
        return {"success": False, "result": str(e)}