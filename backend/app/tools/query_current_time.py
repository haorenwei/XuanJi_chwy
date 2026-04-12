from datetime import datetime

def query_current_time(params: dict) -> dict:
    """
    Query the current time and return it in a formatted string.
    
    Args:
        params (dict): Empty dictionary as no parameters are needed
        
    Returns:
        dict: A dictionary containing success status and the current time
    """
    try:
        current_time = datetime.now()
        time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        return {"success": True, "result": time_str}
    except Exception as e:
        return {"success": False, "result": str(e)}