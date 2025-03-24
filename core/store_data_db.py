import time
from core.event_scheduler import create_event, isRequired
from services.task_creater import create_task
from setups import  health_collection, message_collection, email_collection, \
                    task_collection, insight_collection, call_collection, \
                    daily_sum_collection, weekly_report_collection

# ---------------------------- Process incoming data
def process(ai_response, data, source):
    """Processes the incoming data by categorizing it into messages, tasks, insights, or health data
       and marks the original messages as processed."""

    if not ai_response or "Category" not in ai_response:
        return {"status": "error", "message": "Invalid AI response"}, 400

    # Extract Identifiers
    identifier = {
        "source": source,
        "message_id": data.get("message_id"),
        "email_id": data.get("email_id"),
        "sender": data.get("sender", "Unknown"),
        "timestamp": data.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S")),
    }

    # Store WhatsApp messages or emails (Prevent duplicates)
    if source == "whatsapp" and identifier["message_id"]:
        if ai_response["Category"].lower() in ["business", "personal", "health"]:
            if not message_collection.find_one({"message_id": identifier["message_id"]}):
                message_collection.insert_one(data)
                message_collection.update_one(
                    {"message_id": identifier["message_id"]}, {"$set": {"processed": True}}
                )
    elif source == "email" and identifier["email_id"]:
        if not email_collection.find_one({"email_id": identifier["email_id"]}):
            email_collection.insert_one(data)
            email_collection.update_one(
                {"email_id": identifier["email_id"]}, {"$set": {"processed": True}}
            )

    # Store Health-related data
    if ai_response["Category"].lower() == "health":
        time_stamp = time.strftime("%Y-%m-%d")
        new_msg = data.get("message", "")
        existing = health_collection.find_one({"timestamp": time_stamp})

        if existing:
            message = f"{existing.get('message', '')} {new_msg}".strip()
            health_collection.update_one(
                {"timestamp": time_stamp},
                {"$set": {"message": message}}
            )
        else:
            health_entry = {
            "timestamp": time.strftime("%Y-%m-%d"),
            "message": new_msg,
            }
            health_collection.insert_one(health_entry)

    # Store Tasks
    processed_tasks = []
    if "Tasks" in ai_response and isinstance(ai_response["Tasks"], list):
        for task in ai_response["Tasks"]:
            task_details = {
                "what": task.get("What", ""),
                "when": task.get("When", ""),
                "how": task.get("How", ""),
                "where": task.get("Where", ""),
                "with_whom": task.get("With Whom", ""),
                "priority": ai_response.get("Priority", None),
            }
            
            task_data = create_task(task_details, identifier)
            
            task_collection.insert_one(task_data)
            processed_tasks.append(task_data)

            if isRequired(task_data):
                create_event(task_data)
            else:
                print(f"Skipping task '{task_data['what']}' as it does not require scheduling.")

    # Store Actionable Insights
    processed_insights = []
    if "Actionable_Insights" in ai_response and isinstance(ai_response["Actionable_Insights"], list):
        insight_data = {
            **identifier,
            "insights": ai_response["Actionable_Insights"],
        }
        insight_collection.insert_one(insight_data)
        processed_insights.append(insight_data)

    return {"status": "success", "message": "Data processed successfully"}, 200

# ---------------------------- Filter out unique emails
def filter_email(emails):
    """Filters out emails that already exist in the database."""
    return [email for email in emails if not email_collection.find_one({"email_id": email["email_id"]})]


# ---------------------------- Apple Health Auto Export Data
from core.fetch_health import fetch_health
def store_health_data(data):
    """Stores health data from Apple Health."""
    health_data = fetch_health(data)
    # print(health_data)
    timestamp = health_data["timestamp"]
    excluded_fields = {"message"}
    health_metrics = {key: value for key, value in health_data.items() if key not in excluded_fields}

    # Check if a document with the same timestamp exists
    existing_entry = health_collection.find_one({"timestamp": timestamp})
    if existing_entry:
        # Update existing document with new health metrics
        health_collection.update_one(
            {"timestamp": timestamp},
            {"$set": health_metrics}
        )
    else:
        # Insert a new document
        health_collection.insert_one(health_metrics)

    return {"status": "success", "message": "Health data stored successfully"}, 200

# ---------------------------- Message Daily Summary
def store_daily_summary(date, text):
    data = {
        "date": date,
        "summary": text
    }
    daily_sum_collection.insert_one(data)
    return {"status": "success", "message": "Daily summary stored successfully"}, 200

# ---------------------------- Health Weekly Report
def store_weekly_report(week, text):
    data = {
        "week": week,
        "report": text
    }
    weekly_report_collection.insert_one(data)
    return {"status": "success", "message": "Weekly report stored successfully"}, 200

# ---------------------------- Call Summary
def store_call_summary(data):
    """Stores call summary in the database"""
    call_data = {
        'call_id': data['call_id'],
        'call_type': data['call_type'],
        'caller_number': data['number'],
        'call_time': data['timestamp'],
        'call_summary': data['summary'],
        'callback_required': data['callback_req']
    }
    call_collection.insert_one(call_data)

    return {"status": "success", "message": "Call summary stored successfully"}, 200
