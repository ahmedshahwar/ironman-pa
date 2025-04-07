# import os
import csv
import datetime
from pathlib import Path

from setups import health_collection, message_collection, email_collection, \
                    task_collection, insight_collection, call_collection, \
                    daily_sum_collection, weekly_report_collection

# from pymongo import MongoClient
# from dotenv import load_dotenv

# load_dotenv()

# # ---------------------------- MongoDB setup
# MONGO_URI = os.getenv("MONGO_DB_URI")
# if not MONGO_URI:
#     raise ValueError("MongoDB URI is missing. Check your .env file.")

# try:
#     client = MongoClient(MONGO_URI)
#     db = client['ironman']
# except Exception as e:
#     raise RuntimeError(f"Failed to connect to MongoDB: {e}")

# # ---------------------------- Collection setup
# health_collection = db['health_data']
# message_collection = db['whatsapp_messages']
# email_collection = db['emails']
# task_collection = db['tasks']
# insight_collection = db['insights']

# ---------------------------- Export data for analysis
def csv_for_analysis(purpose: str, date: str):
    """
    Fetches data from MongoDB based on the given purpose and date, writes it to a CSV file,
    and saves it in the 'csv' folder in the main working directory.
    """
    # Validate purpose and date
    if purpose.lower() not in ["daily summary", "weekly health report"]:
        raise ValueError("Invalid purpose. Choose 'daily summary' or 'weekly health report'.")

    try:
        datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Invalid date format. Use 'YYYY-MM-DD'.")

    # Ensure the 'csv' directory exists
    csv_dir = Path("csv")
    csv_dir.mkdir(exist_ok=True)

    # Define CSV filename
    file_name = f"{purpose.replace(' ', '_').lower()}_{date}.csv"
    file_path = csv_dir / file_name

    # Open the CSV file for writing
    with open(file_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        # Fetch data based on the purpose
        if purpose.lower() == "daily summary":
            # Define header for CSV
            header = [
                "Source", "Message ID", "Email ID", "Sender", "Timestamp", "Message",
                "Tasks", "Task Due Date", "Task Location", "Task Method", "Task People", "Task Priority", "Task Status",
                "Insights"
            ]
            writer.writerow(header)

            start_of_day = date
            end_of_day = (datetime.datetime.strptime(date, "%Y-%m-%d") + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

            messages = list(message_collection.find({"timestamp": {"$gte": start_of_day, "$lt": end_of_day}}))
            emails = list(email_collection.find({"timestamp": {"$gte": start_of_day, "$lt": end_of_day}}))
            data_entries = messages + emails

            # Process each message/email and fetch associated tasks & insights
            for entry in data_entries:
                source = "WhatsApp" if "message_id" in entry else "Email"
                message_id = entry.get("message_id", "")
                email_id = entry.get("email_id", "")
                sender = entry.get("sender", "Unknown")
                timestamp = entry.get("timestamp", "")
                message = entry.get("message", "")

                # Fetch related tasks
                tasks = list(task_collection.find({"$or": [{"message_id": message_id}, {"email_id": email_id}]}))
                task_strs = []
                task_due_dates = []
                task_locations = []
                task_methods = []
                task_people = []
                task_priorities = []
                task_statuses = []

                for task in tasks:
                    task_strs.append(task.get("what", ""))
                    task_due_dates.append(task.get("when", ""))
                    task_locations.append(task.get("where", ""))
                    task_methods.append(task.get("how", ""))
                    task_people.append(task.get("with_whom", ""))
                    task_priorities.append(task.get("priority", ""))
                    task_statuses.append(task.get("status", "pending"))

                # Join multiple tasks with a separator
                task_strs = " | ".join([task if task is not None else "" for task in task_strs])
                task_due_dates = " | ".join([date if date is not None else "" for date in task_due_dates])
                task_locations = " | ".join([loc if loc is not None else "" for loc in task_locations])
                task_methods = " | ".join([method if method is not None else "" for method in task_methods])
                task_people = " | ".join([person if person is not None else "" for person in task_people])
                task_priorities = " | ".join([priority if priority is not None else "" for priority in task_priorities])
                task_statuses = " | ".join([status if status is not None else "" for status in task_statuses])

                # Fetch related insights
                insights = list(insight_collection.find({"$or": [{"message_id": message_id}, {"email_id": email_id}]}))
                insights_str = " | ".join([", ".join(i.get("insights", [])) for i in insights])

                # Write to CSV
                writer.writerow([
                    source, message_id, email_id, sender, timestamp, message,
                    task_strs, task_due_dates, task_locations, task_methods, task_people, task_priorities, task_statuses,
                    insights_str
                ])

            return str(file_path)

        elif purpose.lower() == "weekly health report":
            start_date = (datetime.datetime.strptime(date, "%Y-%m-%d") - datetime.timedelta(days=6)).strftime("%Y-%m-%d")
            try:
                health_data = list(health_collection.find({"timestamp": {"$gte": start_date, "$lte": date}}))
            except Exception as e:
                print(f"Error fetching health data: {e}")
                health_data = []

            headers = [
                "Timestamp",
                "Flights Climbed", "Active Energy", "Basal Energy Burned", "Step Count", "Walking Running Distance", "Headphone Audio Exposure",
                "Walking Step Length", "Walking Speed", "Walking Asymmetry Percentage", "Walking Double Support Percentage",
                "Heart Rate",
                "Message"
            ]
            writer.writerow(headers)
            for entry in health_data:
                writer.writerow([
                    entry.get("timestamp", ""),  # Timestamp
                    entry.get("flights_climbed", ""),  # Flights Climbed
                    entry.get("active_energy", ""),  # Active Energy
                    entry.get("basal_energy_burned", ""),  # Basal Energy Burned
                    entry.get("step_count", ""),  # Step Count
                    entry.get("walking_running_distance", ""),  # Walking Running Distance
                    entry.get("headphone_audio_exposure", ""),  # Headphone Audio Exposure
                    entry.get("walking_step_length", ""),  # Walking Step Length
                    entry.get("walking_speed", ""),  # Walking Speed
                    entry.get("walking_asymmetry_percentage", ""),  # Walking Asymmetry Percentage
                    entry.get("walking_double_support_percentage", ""),  # Walking Double Support Percentage
                    entry.get("hr", ""),  # Heart Rate
                    entry.get("message", "")  # Message
                ])

            return str(file_path)

        else:
            raise ValueError("Invalid purpose. Choose 'daily summary' or 'weekly health report'.")
            return None


def fetch_data(collection, criteria):
    """
    Fetches data from a specified MongoDB collection based on given criteria.
    Returns the data in a structured format.
    """

    if collection == "message_collection":
        col_ = message_collection
    elif collection == "email_collection":
        col_ = email_collection
    elif collection == "health_collection":
        col_ = health_collection
    elif collection == "call_collection":
        col_ = call_collection
    elif collection == "daily_sum_collection":
        col_ = daily_sum_collection
    elif collection == "weekly_report_collection":
        col_ = weekly_report_collection
    else:
        return f"[ERROR]: Invalid collection name."    
    try:
        data = list(col_.find(criteria))
        return data
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None