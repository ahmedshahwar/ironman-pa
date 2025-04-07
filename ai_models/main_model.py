import json, os
from datetime import datetime
from setups import llm, llm_small

from core.bookings import AmadeusBookingEngine
from core.event_scheduler import create_event, delete_event, fetch_events
from core.fetch_data_db import fetch_data

HISTORY = r"ai_models\history.json"
if os.path.exists(HISTORY):
    with open(HISTORY, 'r') as f:
        conv_hist = json.load(f)
else:
    conv_hist = []

with open(r"prompts\react_intent.txt", 'r') as f:
    INTENT_PROMPT = f.read().strip()

with open(r"prompts\react_response.txt", 'r') as f:
    RESPONSE_PROMPT = f.read().strip()

# -------------------- Main AI functions
def react_handler(user_text):
    global conv_hist
    error = None
    data = ""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conv = '\n'.join([f"{entry['role']}: {entry['content']}" for entry in conv_hist])
    
    prompt = (
        INTENT_PROMPT
        .replace("{conversation_history}", conv)
        .replace("{current_time}", current_time)
        .replace("{user_query}", user_text)
    )
    
    response = llm_small.invoke(prompt)
    try:
        intent_response = json.loads(response.content)
    except Exception as e:
        error = "[ERROR]: Invalid response from the LLM: Please contact developer"
        intent_response = {}
    
    error = intent_response.get("error")
    intent = intent_response.get("intent")
    actions = intent_response.get("actions")
    
    if not intent:
        error = "[ERROR]: Intent not found in response."
    
    if not error and actions:
        details = actions.get("details", actions.get("event_details", {}))
        if details:
            error = details.get("error")
    
    # Handle MongoDB Intents
    mongo_intents = [
        "fetching_messages", "fetching_emails", "fetching_health_records",
        "fetching_daily_summary", "fetching_weekly_report", "fetching_call_data"
    ]
    
    if not error and intent and intent.lower() in mongo_intents:
        if not isinstance(actions, dict) or actions.get("type") != "mongo_query":
            error = "[ERROR]: Missing or invalid mongo_query action."
        else:
            collection = actions.get("collection")
            criteria = actions.get("criteria")
            if not collection or not isinstance(criteria, dict):
                error = "[ERROR]: MongoDB query missing collection or criteria."
            else:
                try:
                    data = fetch_data(collection, criteria)
                except Exception as e:
                    error = f"[ERROR]: Error fetching data from {collection}: {str(e)}"
    
    # Handle Calendar Intent
    elif not error and intent and intent.lower() == "calendar":
        if not isinstance(actions, dict):
            error = "[ERROR]: Missing calendar action object."
        else:
            event_type = actions.get("type")
            event_details = actions.get("event_details")
            if not event_details or not isinstance(event_details, dict):
                error = "[ERROR]: Missing or invalid event_details."
            else:
                time_str = event_details.get("time")
                if not time_str:
                    error = "[ERROR]: Event time is required."
                else:
                    try:
                        datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        error = "[ERROR]: Invalid date format. Use YYYY-MM-DD HH:MM:SS."
                if not error:
                    if event_type == "create":
                        if not event_details.get("purpose"):
                            error = "[ERROR]: Purpose is required to create an event."
                        else:
                            try:
                                if create_event(event_details):
                                    data = "Event created successfully"
                                else:
                                    data = "Failed to create event."
                            except Exception as e:
                                error = f"[ERROR]: Error creating event: {str(e)}"
                    elif event_type == "delete":
                        try:
                            if delete_event(when=time_str):
                                data = "Event deleted successfully"
                            else:
                                data = "No event found to delete."
                        except Exception as e:
                            error = f"[ERROR]: Error deleting event: {str(e)}"
                    elif event_type == "search":
                        try:
                            data = fetch_events(when=time_str)
                        except Exception as e:
                            error = f"[ERROR]: Error fetching events: {str(e)}"
                    else:
                        error = f"[ERROR]: Unknown calendar action type: {event_type}"
    
    # Handle Flight and Hotel Booking Intent 
    elif not error and intent and intent.lower() == "booking_flight":
        if not isinstance(actions, dict) or actions.get("type") != "booking_request":
            error = "[ERROR]: Missing or invalid booking request for flight."
        else:
            details = actions.get("details")
            if not details:
                error = "[ERROR]: Missing flight booking details."
            else:
                origin = details.get("departure_location")
                destination = details.get("arrival_location")
                departure_date = details.get("date")
                adults = details.get("adults", 1)
                if not all([origin, destination, departure_date]):
                    error = "[ERROR]: Flight booking requires origin, destination, and departure_date."
                else:
                    try:
                        data = AmadeusBookingEngine().search_flights(origin, destination, departure_date, adults)
                    except Exception as e:
                        error = f"[ERROR]: Flight booking failed: {str(e)}"
    
    elif not error and intent and intent.lower() == "booking_hotel":
        if not isinstance(actions, dict) or actions.get("type") != "booking_request":
            error = "[ERROR]: Missing or invalid booking request for hotel."
        else:
            details = actions.get("details")
            if not details:
                error = "[ERROR]: Missing hotel booking details."
            else:
                city_code = details.get("location")
                check_in_date = details.get("check_in")
                check_out_date = details.get("check_out")
                if not all([city_code, check_in_date, check_out_date]):
                    error = "[ERROR]: Hotel booking requires location, check_in, and check_out."
                else:
                    try:
                        data = AmadeusBookingEngine().search_hotels(city_code, check_in_date, check_out_date)
                    except Exception as e:
                        error = f"[ERROR]: Hotel booking failed: {str(e)}"
    
    # Other Intents
    else:
        data = ""
    
    if error:
        data = error
    
    conv_hist.append({"role": "user", "content": user_text})
    res_prompt = (
        RESPONSE_PROMPT
        .replace("{conversation_history}", conv)
        .replace("{current_time}", current_time)
        .replace("{user_query}", user_text)
        .replace("{intent}", intent if intent else "other")
        .replace("{backend_response}", str(data))
    )
    
    final_response = llm.invoke(res_prompt)
    ai_response = str(final_response.content)
    
    conv_hist.append({"role": "assistant", "content": ai_response})
    conv_hist = conv_hist[-24:]
    with open(HISTORY, 'w', encoding='utf-8') as f:
        json.dump(conv_hist, f, indent=2)
    
    return ai_response