import os
from dotenv import load_dotenv

load_dotenv()

from setups import twilio_client, CLIENT_NUMBER, TWILIO_NUMBER

# # ---------------------------- Twilio setup
# account_sid = os.getenv("ACCOUNT_SID")
# auth_token = os.getenv("AUTH_TOKEN")
# if not account_sid or not auth_token:
#     raise ValueError("Twilio credentials missing. Check your .env file.")

# from twilio.rest import Client
# client = Client(account_sid, auth_token)

# CLIENT_NUMBER = os.getenv("CLIENT_NUMBER")
# TWILIO_NUMBER =os.getenv("TWILIO_NUMBER")

# ---------------------------- Sending Message
def send_msg_self(text):
    msg = twilio_client.messages.create(
        to=CLIENT_NUMBER, from_=TWILIO_NUMBER, body=text
    )

    return "Message sent successfully", 200

def send_msg(text, to):
    msg = twilio_client.messages.create(
        to=to, from_=TWILIO_NUMBER, body=text
    )

    return f"Message sent to {to} successfully", 200