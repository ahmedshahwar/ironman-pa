import os
from dotenv import load_dotenv
from twilio.rest import Client
from pymongo import MongoClient
from langchain_openai import ChatOpenAI
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# ---------------------------- Twilio Setup
account_sid = os.getenv("ACCOUNT_SID")
auth_token = os.getenv("AUTH_TOKEN")
if not account_sid or not auth_token:
    raise ValueError("Twilio credentials missing. Check your .env file.")

twilio_client = Client(account_sid, auth_token)
FROM = os.getenv("TWILIO_NUMBER").split(":")[-1]
CLIENT_NUMBER = os.getenv("CLIENT_NUMBER")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")

# ---------------------------- MongoDB Setup
MONGO_URI = os.getenv("MONGO_DB_URI")
if not MONGO_URI:
    raise ValueError("MongoDB URI is missing. Check your .env file.")

try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client['ironman']
except Exception as e:
    raise RuntimeError(f"Failed to connect to MongoDB: {e}")

# ---------------------------- MongoDB Collections
health_collection = db['health_data']
message_collection = db['whatsapp_messages']
email_collection = db['emails']
task_collection = db['tasks']
insight_collection = db['insights']
call_collection = db['calls']
daily_sum_collection = db['daily_summary']
weekly_report_collection = db['weekly_report']

# ---------------------------- OpenAI Setup
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key is missing. Check your .env file.")

llm = ChatOpenAI(model="gpt-4-turbo", temperature=0.5, streaming=True, api_key=OPENAI_API_KEY)
llm_small = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.5, api_key=OPENAI_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------------------- Ngrok Setup
NGROK_URL = os.getenv("NGROK_URL")
if not NGROK_URL:
    raise ValueError("Ngrok URL is missing. Check your .env file.")

# ---------------------------- Deepgram Setup
DEEPGRAM_API = os.getenv("DEEPGRAM_API")