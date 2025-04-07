from setups import llm, llm_small, openai_client, task_collection
from datetime import datetime
# ---------------------------- Main AI Function
conv_hist = {}  # Store conversation history

with open(r"prompts/outgoing_call.txt", 'r') as f:
    OUTBOUND_PROMPT = f.read().strip()

with open(r"prompts/incoming_call.txt", 'r') as f:
    INBOUND_PROMPT = f.read().strip()

def ai_model(text, context, history, appt=None, call_type=None):
    """Generates AI Responses using OpenAI while maintaining conversation history."""
    prompt_template = OUTBOUND_PROMPT if call_type else INBOUND_PROMPT
    time_ = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    prompt = f"""{prompt_template}\n\n
        Current Time: {time_}\n\n
        Call Type: {call_type or "N/A"}\n\n
        Context from past conversations: {context}\n\n
        Conversation history till this point: {history}\n\n
        Appointment Availability: {appt}\n\n
        New Input: {text}"""
    
    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return "I'm sorry, I couldn't process that. Could you please repeat?"

# ---------------------------- Handling calls
from services.call import check_intent, extract_details, tts_engine, extract_time, generate_call_summary
from core.event_scheduler import check_availability, create_event, fetch_events, delete_event
from core.store_data_db import store_call_summary
from services.task_creater import create_task

async def call(call_id, number, start_time, context, user_input=None, call_type=None):
    """Handles incoming and outgoing calls, processes user input, and executes intent-based actions."""
    # Fetch conversation history
    history = conv_hist.setdefault(call_id, []) 
    if user_input:
        history.append({"role": "user", "content": user_input})
        conv_hist[call_id] = history

    # Determine intent
    intent = check_intent(conv_hist, call_id, llm_small)
    intent = 'none' if not intent['intent'] else intent['intent']

    appt_status = None  # Appointment status for response generation
    if intent in ["schedule_appt", "reschedule_appt"]:
        task_details = {
            "what": None, "when": None, "how": None, "where": None, "with_whom": None, "status": "pending"
        }
        identifier = {
            "source": "call",
            "call_id": call_id,
            "timestamp": datetime.fromisoformat(start_time).strftime("%Y-%m-%d %H:%M:%S"),
        }

        event_details = fetch_events(number) if intent == "reschedule_appt" else None
        extracted_details = extract_details(conv_hist, call_id, llm_small, event_details)
        print("Extracted details:", extracted_details)
        task_details.update(extracted_details)
        print("Task Details:", task_details)

        if not task_details["when"] or not task_details["when"].strip() or not task_details["what"] or not task_details["what"].strip():
            appt_status = "details missing"
        elif task_details["when"]:
            extracted_time = extract_time(task_details["when"])
            if extracted_time and check_availability(extracted_time):
                task_data = create_task(task_details, identifier)
                task_collection.insert_one(task_data)
                create_event(task_data)
                appt_status = "rescheduled" if intent == "reschedule_appt" else "available"
            else:
                appt_status = "unavailable"

        # Cancel previous appointment if rescheduling
        if intent == "reschedule_appt" and event_details:
            delete_event(event_id=event_details["event_id"])
            task_collection.update_one(
                {"task_id": event_details["task_id"]}, {"$set": {"status": "cancelled"}}
            )

    elif intent == "cancel_appt":
        event_details = fetch_events(number)
        if event_details and delete_event(event_id=event_details["event_id"]):
            task_collection.update_one(
                {"task_id": event_details["task_id"]}, {"$set": {"status": "cancelled"}}
            )
            appt_status = "cancelled"
        else:
            appt_status = "appt not found"
            
    
    print("Appointment Status:",appt_status)
    # Generate AI response
    ai_response = ai_model(user_input, context, history, appt_status, call_type)
    history.append({"role": "assistant", "content": ai_response})
    conv_hist[call_id] = history
    print(ai_response)
    
    # Generate TTS output
    audio_output = await tts_engine(ai_response)

    # Handling call summary generation at the end of the call
    if any(phrase in ai_response.lower() for phrase in ["goodbye", "have a nice day", "bye"]):
        conversation = "\n".join([f"{entry['role']}: {entry['content']}" for entry in conv_hist.get(call_id, [])])
        call_ = "Outbound" if call_type else "Inbound"
        call_summary = generate_call_summary(conversation, call_id, number, call_, start_time, llm_small)
        store_call_summary(call_summary)

    return audio_output
