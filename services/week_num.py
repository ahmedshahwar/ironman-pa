import datetime


def get_week_number(reference_day="Monday", offset_weeks=0):
    """
    Gets the ISO week number based on a user-defined reference day.
    `offset_weeks` allows shifting back by full weeks.
    """
    today = datetime.date.today()
    # Get ISO weekday (Monday = 1, Sunday = 7)
    today_weekday = today.isoweekday()

    # Map user-friendly day names to ISO numbers
    days_map = {
        "Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4,
        "Friday": 5, "Saturday": 6, "Sunday": 7
    }
    
    reference_weekday = days_map.get(reference_day, 1)  # Default to Monday

    # Move back to the most recent chosen weekday
    days_offset = (today_weekday - reference_weekday) % 7
    reference_date = today - datetime.timedelta(days=days_offset)  

    # Adjust for offset weeks
    reference_date -= datetime.timedelta(weeks=offset_weeks)

    return reference_date.isocalendar()[1]