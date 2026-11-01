from datetime import datetime, date, timedelta

def format_relative_date(date_str: str) -> str:
    """Return friendly relative date strings like 'Today', 'Tomorrow', 'Due in 2 days', or 'Overdue'."""
    if not date_str:
        return "No deadline"
    
    try:
        if isinstance(date_str, datetime):
            target_date = date_str.date()
        elif isinstance(date_str, date):
            target_date = date_str
        else:
            target_date = datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
        
        today = date.today()
        diff = (target_date - today).days

        if diff < 0:
            return f"Overdue by {abs(diff)} day{'s' if abs(diff) > 1 else ''}"
        elif diff == 0:
            return "Due Today"
        elif diff == 1:
            return "Due Tomorrow"
        elif diff <= 7:
            return f"Due in {diff} days"
        else:
            return target_date.strftime("%b %d, %Y")
    except Exception:
        return str(date_str)

def get_day_name(day_index: int) -> str:
    """Convert 0-6 index to day name (0=Monday, 6=Sunday)."""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if 0 <= day_index <= 6:
        return days[day_index]
    return "Unknown"

def format_minutes_to_hours(minutes: int) -> str:
    """Format minutes into human readable '2h 15m' format."""
    if not minutes or minutes <= 0:
        return "0m"
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0 and mins > 0:
        return f"{hours}h {mins}m"
    elif hours > 0:
        return f"{hours}h"
    return f"{mins}m"
