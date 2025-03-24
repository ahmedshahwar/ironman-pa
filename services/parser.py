from datetime import datetime, timedelta, time
from core.event_scheduler import check_availability

def get_next_available_time(event_time):
    """
    Finds the next available time slot in 15-minute intervals for scheduling.
    Ensures the time is within business hours (9:00 AM to 5:00 PM).
    Continues checking until an available slot is found.
    """
    while True:
        if event_time.time() < time(9, 0) or event_time.time() >= time(17, 0):
            event_time = datetime.combine(event_time.date() + timedelta(days=1), time(9, 0))
            continue

        if check_availability(event_time):
            return event_time
        event_time += timedelta(minutes=15)


def parse_when(when_str):
    """
    Parses a datetime string in YYYY-MM-DD HH:MM:SS format into a datetime object.
    Adjusts for business hours and checks for availability in Google Calendar.
    """
    try:
        event_time = datetime.strptime(when_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

    event_time = get_next_available_time(event_time)
    return event_time







# def parse_when(when_str, scheduled_events=None):
#     """Parses a natural language date and time string into a datetime object."""
#     now = datetime.now()
#     today = now.date()
#     when_lower = when_str.lower()

#     # Initialize date and time
#     date = None
#     parsed_time = None

#     # Detect specific date formats (YYYY-MM-DD, "March 10, 2025", "10th March")
#     try:
#         date = datetime.strptime(when_str, "%Y-%m-%d").date()
#     except ValueError:
#         pass

#     # Detect dates like "10th March" or "March 10"
#     if not date:
#         date_match = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December)', when_lower)
#         if date_match:
#             day, month = date_match.groups()
#             year = now.year  # Default to the current year
#             try:
#                 date = datetime.strptime(f"{day} {month} {year}", "%d %B %Y").date()
#             except ValueError:
#                 pass

#     # Detect "on the 25th", "on 5th of April"
#     if not date:
#         ordinal_match = re.search(r'on the (\d{1,2})(?:st|nd|rd|th)?(?: of (\w+))?', when_lower)
#         if ordinal_match:
#             day, month = ordinal_match.groups()
#             month = month if month else now.strftime("%B")  # Use current month if not provided
#             year = now.year
#             try:
#                 date = datetime.strptime(f"{day} {month} {year}", "%d %B %Y").date()
#             except ValueError:
#                 pass

#     # Detect relative days
#     if not date:
#         if "today" in when_lower:
#             date = today
#         elif "tomorrow" in when_lower:
#             date = today + timedelta(days=1)
#         elif "next week" in when_lower:
#             days_until_monday = (7 - today.weekday()) % 7 + 1
#             date = today + timedelta(days=days_until_monday)

#     # Detect weekdays (e.g., "Monday", "next Friday")
#     if not date:
#         days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
#         for idx, day in enumerate(days):
#             if day in when_lower:
#                 target_weekday = idx
#                 current_weekday = now.weekday()
#                 days_until_target = (target_weekday - current_weekday) % 7
#                 days_until_target = 7 if days_until_target == 0 and "next" in when_lower else days_until_target
#                 date = today + timedelta(days=days_until_target)
#                 break

#     # Default to today if no date found
#     date = date or today

#     # Extract time (formats like "10 AM", "10:30 PM", "15:00", "at 9 in the morning")
#     time_pattern = re.compile(r'(\d{1,2}(:\d{2})?\s*(AM|PM)?)', re.IGNORECASE)
#     match = time_pattern.search(when_str)

#     if match:
#         time_str = match.group(0).strip().upper()
#         try:
#             if ":" in time_str:
#                 parsed_time = datetime.strptime(time_str, "%I:%M %p").time() if "AM" in time_str or "PM" in time_str else datetime.strptime(time_str, "%H:%M").time()
#             else:
#                 parsed_time = datetime.strptime(time_str, "%I %p").time() if "AM" in time_str or "PM" in time_str else datetime.strptime(time_str, "%H").time()
#         except ValueError:
#             parsed_time = None
#     else:
#         parsed_time = None

#     # If no time provided, default to 9:00 AM
#     if not parsed_time:
#         parsed_time = time(9, 0)

#     # Combine date and time
#     event_time = datetime.combine(date, parsed_time)

#     # Adjust for past events
#     if event_time < now:
#         event_time += timedelta(days=7) if "next" in when_lower else timedelta(days=1)

#     # Get the next available time slot if needed
#     if scheduled_events is not None:
#         event_time = get_next_available_time(event_time.date(), scheduled_events, event_time.time())

#     return event_time