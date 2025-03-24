from datetime import datetime, timedelta, timezone
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Define the scopes for Google Calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar']

def authenticate_google_calendar():
    creds = None
    token_path = os.path.join('secrets', 'token.json') # Path to the token.json

    # Check if the token.json file exists
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # If there are no valid credentials, authenticate the user
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            credentials_path = os.path.join('secrets', 'credentials.json') # Path to the credentials.json 
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials to the token.json file inside the secrets folder
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    try:
        # Build the Google Calendar API service
        service = build('calendar', 'v3', credentials=creds)
        return service
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def isRequired(task):
    """Determines if a task should be added to Google Calendar based on keywords."""
    keywords = [
        "meeting", "call", "appointment", "appt", "reminder",
        "event", "schedule", "deadline", "due date", "task",
        "conference", "webinar", "workshop", "seminar", "interview",
        "lunch", "dinner", "breakfast", "coffee", "hangout",
        "check-in", "catch-up", "review", "planning", "discussion",
        "presentation", "demo", "training", "session", "consultation",
        "reservation", "booking", "party", "celebration", "anniversary",
        "birthday", "holiday", "vacation", "trip", "travel",
        "flight", "doctor", "dentist", "therapy", "consultation",
        "exam", "test", "interview", "audition", "rehearsal",
        "submission", "delivery", "launch", "release", "milestone",
        "goal", "target", "checkpoint"
    ]
    return any(k in task.get('what', "").lower() for k in keywords)

def check_availability(event_time):
    """Checks if the time slot is available in Google Calendar"""
    end_time = event_time + timedelta(minutes=15)
    service = authenticate_google_calendar()

    event_res = service.events().list(
        calendarId='primary',
        timeMin=event_time.isoformat() + 'Z',
        timeMax=end_time.isoformat() + 'Z',
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    return not event_res.get('items', [])

def fetch_events(task_id=None, number=None):
    """Fetches future events from Google Calendar based on task_id or number."""
    if not task_id and not number:
        print("Either task_id or number is required")
        return []

    # Normalize the number (remove 'whatsapp:' if present)
    if number and ':' in number:
        number = number.split(':')[-1]

    service = authenticate_google_calendar()
    now = datetime.now(timezone.utc).isoformat()

    # Build the query filter for private extended properties
    query_filter = []
    if task_id:
        query_filter.append(f"task_id={task_id}")
    if number:
        query_filter.append(f"sender={number}")
        query_filter.append(f"sender=whatsapp:{number}")

    try:
        # Fetch only the events that match the query and are in the future
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            singleEvents=True,
            orderBy="startTime",
            privateExtendedProperty=query_filter  # Pass list of filters
        ).execute()

        events = events_result.get('items', [])
        
        # Extract relevant event details
        event_details = [
            {
                'event_id': event['id'],
                'task_id': event['task_id'],
                'time': event.get('start', "No Time"),
                'summary': event.get('summary', 'No Title'),
                'description': event.get('description', 'No Description')
            }
            for event in events
        ]
        return event_details

    except HttpError as error:
        print(f"Failed to fetch events: {error}")
        return []


from services.parser import parse_when
from core.message_sender import send_msg
def create_event(task):
    """
    Creates an event in Google Calendar based on the provided task.
    Sends a confirmation message to the sender indicating the scheduled time.
    """
    summary = task.get("what", "Task")
    description = f"""
        Task: {task.get('task_id', '')}\n
        Task From: {task.get('sender', '')}\n
        What: {task.get('what', '')}\n
        How: {task.get('how', '')}\n
        Where: {task.get('where', '')}\n
        With Whom: {task.get('with_whom', '')}"""
    
    when_str = task.get("when", "")

    # Parse the 'when' field into a datetime object
    event_time = parse_when(when_str)
    if not event_time:
        print(f"Skipping task '{summary}' due to invalid 'when' field: {when_str}")
        return

    # Set the end time to 15 minutes after the start time
    end_time = event_time + timedelta(minutes=15)

    # Define the event
    event = {
        'summary': summary,
        'description': description,
        'start': {'dateTime': event_time.isoformat(), 'timeZone': 'Asia/Karachi'},
        'end': {'dateTime': end_time.isoformat(), 'timeZone': 'Asia/Karachi'},
        'extendedProperties': {  # Can be used later to fetch the details using these attributes
            'private': {
                'task_id': task.get('task_id', ''),
                'number': task.get('sender', '')
            }
        }
    }

    # Parse the requested time for comparison
    try:
        requested_time = datetime.strptime(when_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        requested_time = None

    # Get the sender's contact information
    TO = task.get("sender", "")

    # Prepare the confirmation message
    if requested_time and event_time == requested_time:
        message = f"Your meeting has been scheduled at {event_time.strftime('%Y-%m-%d %H:%M:%S')}."
    else:
        message = f"The requested time is unavailable. Your meeting has been scheduled at {event_time.strftime('%Y-%m-%d %H:%M:%S')} instead."

    # Authenticate and get the Google Calendar service
    service = authenticate_google_calendar()
    if service:
        try:
            # Create the event in Google Calendar
            event = service.events().insert(calendarId='primary', body=event).execute()
            print(f'Event created: {event.get("htmlLink")}')

            # Send the confirmation message to the sender
            if TO:
                send_msg(text=message, to=TO)
        except HttpError as error:
            print(f"Failed to create event: {error}")
            if TO:
                send_msg(text="Failed to schedule event at this moment. Please try again later.", to=TO)


def delete_event(event_id=None, task_id=None, number=None):
    """
    Deletes an event from Google Calendar using event_id, task_id, or number.
    If multiple events match task_id or number, all of them will be deleted.
    """
    if not event_id and not task_id and not number:
        print("Either event_id, task_id, or number is required")
        return False

    service = authenticate_google_calendar()

    try:
        # If event_id is provided, delete the event directly
        if event_id:
            service.events().delete(calendarId='primary', eventId=event_id).execute()
            print(f"Event {event_id} deleted successfully.")
            return True

        # If task_id or number is provided, find matching events first
        matching_events = fetch_events(task_id=task_id, number=number)

        if not matching_events:
            print("No matching events found to delete.")
            return False

        # Delete all matching events
        for event in matching_events:
            service.events().delete(calendarId='primary', eventId=event['event_id']).execute()
            print(f"Deleted event: {event['event_id']}")

        return True

    except HttpError as error:
        print(f"Failed to delete event: {error}")
        return False