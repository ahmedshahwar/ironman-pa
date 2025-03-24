import csv
import os
from pathlib import Path
from datetime import datetime, timedelta

# Constants
CSV_DIR = Path("csv")
CSV_DIR.mkdir(exist_ok=True)  # Ensure the CSV directory exists


def delete_old_files():
    """Deletes CSV files older than 1 day."""
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    for file in CSV_DIR.glob("*.csv"):
        if yesterday in file.name:
            try:
                os.remove(file)
                print(f"Deleted old file: {file}")
            except Exception as e:
                print(f"Error deleting {file}: {e}")


def save_to_csv(data, file_prefix, fieldnames):
    """Helper function to save data to a CSV file."""
    delete_old_files()  # Clean up old files before writing
    today_date = datetime.now().strftime("%Y-%m-%d")
    file_path = CSV_DIR / f"{file_prefix}_{today_date}.csv"
    file_exists = file_path.exists()

    with file_path.open(mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader() # if no data in file
        writer.writerow(data)


def csv_email(email):
    """Saves email data to a daily CSV file."""
    email_data = {
        "email_id": email["email_id"],
        "sender": email["sender"],
        "subject": email["subject"],
        "date": email["date"],
        "body": email.get("body", ""),
        "logged_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_to_csv(email_data, "csv_emails", ["email_id", "sender", "subject", "date", "body", "logged_at"])


def csv_msg(message):
    """Saves message data to a daily CSV file."""
    message_data = {
        "message_id": message["message_id"],
        "sender": message["sender"],
        "message": message["message"],
        "timestamp": message["timestamp"],
        "logged_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_to_csv(message_data, "csv_messages", ["message_id", "sender", "message", "timestamp", "logged_at"])