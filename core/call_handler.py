from setups import llm, llm_small, openai_client, task_collection
from datetime import datetime
# ---------------------------- Main AI Function
conv_hist = {}  # Store conversation history

def ai_model(call_id, text, context, appt=None, call_type=None):
    """Generates AI Responses using OpenAI while maintaining conversation history."""
    prompt_file = r"prompts/outbound_prompt.txt" if call_type else r"prompts/incoming_call.txt"
    with open(prompt_file, 'r') as f:
        prompt_template = f.read().strip()
    
    history = conv_hist.get(call_id, [])

    if not call_type:
        prompt = f"""{prompt_template}\n\n
            Context from past conversations: {context}\n\n
            Conversation history till this point: {history}\n\n
            Appointment Availability: {appt}\n\n
            New Input: {text}"""
    else:
        prompt = f"""{prompt_template}\n\n
            Call Type: {call_type}\n\n
            Context from past conversations: {context}\n\n
            Conversation history till this point: {history}\n\n
            Appointment Availability: {appt}\n\n
            New Input: {text}"""
    
    try:
        response = llm.invoke(prompt)
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": response.content})
        conv_hist[call_id] = history
        return response.content
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return "Error: AI response not generated"
# ---------------------------- Handling calls
from services.call import check_intent, extract_details, tts_engine, extract_time, generate_call_summary
from core.event_scheduler import check_availability, create_event, fetch_events, delete_event
from core.store_data_db import store_call_summary
from services.task_creater import create_task

def call(call_id, number, start_time, context, user_input=None, call_type=None):
    """Handles incoming and outgoing calls, processes user input, and executes intent-based actions."""
    # Generate AI response in chunks
    ai_response = ai_model(call_id, user_input, context, None, call_type)
    print(ai_response)
    audio_output = tts_engine(ai_response, openai_client)

    # Determine intent
    intent = check_intent(conv_hist, call_id, llm_small)
    intent = 'none' if not intent['intent'] else intent['intent']
    print(intent)
    appt_status = None  # Appointment status for response generation

    if intent in ["schedule_appt", "reschedule_appt"]:
        task_details = {
            "what": None, "when": None, "how": None, "where": None, "with_whom": None, "status": "pending"
        }
        start_time = datetime.fromisoformat(start_time)
        identifier = {
            "source": "call",
            "call_id": call_id,
            "timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        event_details = fetch_events(number) if intent == "reschedule_appt" else None
        extracted_details = extract_details(conv_hist, call_id, llm_small, event_details)
        task_details.update(extracted_details)

        if not task_details["when"]:
            appt_status = "when details missing"
        elif check_availability(extract_time(task_details["when"])):
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

    # Generate AI response based on appointment status
    if appt_status:
        response = ai_model(call_id, user_input, context, appt_status, call_type)
        print(response)
        audio_output = tts_engine(ai_response + response, openai_client)

    # Handling call summary generation at the end of the call
    if any(phrase in ai_response.lower() for phrase in ["goodbye", "have a nice day"]):
        conversation = "\n".join([f"{entry['role']}: {entry['content']}" for entry in conv_hist.get(call_id, [])])
        call_ = "Outbound" if call_type else "Inbound"
        call_summary = generate_call_summary(conversation, call_id, number, call_, start_time, llm_small)
        store_call_summary(call_summary)

    return audio_output
