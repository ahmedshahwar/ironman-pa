import base64, json, asyncio, websockets, os
from flask import Flask, jsonify, request, Response
from flask_sock import Sock
from dotenv import load_dotenv    
from datetime import datetime

load_dotenv()
app = Flask(__name__)
sock = Sock(app)

# ---------------------------- Twilio webhook endpoint
from core.fetch_msg import fetch_msg
from ai_models.model import classify_text
from core.store_data_db import process

@app.route("/webhook", methods=["POST"])
def webhook():
    message_id = request.form.get('MessageSid', '')
    if not message_id:
        return "Invalid request: Missing message ID", 400

    message_data = fetch_msg(request.form)  # Process incoming message
    ai_msg = classify_text(message_data["message"])  # Classify the message
    process(ai_msg, message_data, source="whatsapp")
    
    return "Message received", 200  

# ---------------------------- Gmail webhook endpoint
# ---- Email configuration
IMAP_SERVER = 'imap.gmail.com'
EMAIL_ACCOUNT = os.getenv("EMAIL_ACCOUNT")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

if not EMAIL_ACCOUNT or not EMAIL_PASSWORD:
    raise ValueError("Email credentials missing. Check your .env file.")

from core.fetch_email import fetch_mail
from core.store_data_db import filter_email

@app.route("/fetch_email", methods=["GET"])
def fetch_email():
    # Process Emails (by default it fetches top 5 emails, but you can change it by adding max_emails parameter)
    emails = fetch_mail(IMAP_SERVER, EMAIL_ACCOUNT, EMAIL_PASSWORD)

    if not isinstance(emails, list):
        return jsonify({"status": "error", "message": "Failed to fetch emails from Gmail."}), 500
    
    unique_emails = filter_email(emails)

    if not unique_emails:
        return jsonify({"status": "success", "message": "No new emails to save."}), 200

    for email in unique_emails:
        ai_email = classify_text(email["body"])
        process(ai_email, email, source="email")
    
    return "Emails processed successfully", 200

# ---------------------------- Health Auto Export endpoint
from core.store_data_db import store_health_data
@app.route("/get_health", methods=["POST", "GET"])
def get_health_data():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Invalid JSON data"}), 400
        store_health_data(data)
        return jsonify({"status": "success", "message": "Data received"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ---------------------------- AI Summary & Report Generation
from core.fetch_data_db import csv_for_analysis
from ai_models.model import generate_summary, generate_report
from core.message_sender import send_msg_self
from core.store_data_db import store_daily_summary, store_weekly_report

@app.route("/generate_summary", methods=["POST", "GET"])
def daily_summary():
    """Generates daily summary of all the message and emails received. Sends the summary via whatsapp and saves it in database."""

    date=datetime.datetime.now().strftime("%Y-%m-%d")
    csv_path = csv_for_analysis("daily summary", date=date)
    summary = generate_summary(csv_path)
    sent = send_msg_self(summary)
    saving = store_daily_summary(date, summary)

    if summary == "Error: CSV file not found.":
        return summary, 404
    return "Summary generated", 200


@app.route("/generate_report", methods=["POST", "GET"])
def weekly_report():
    """Generates weekly report of the health data. Sends the report via whatsapp and saves it in database."""

    date=datetime.datetime.now().strftime("%Y-%m-%d")
    csv_path = csv_for_analysis("weekly health report", date=date)  # Generate weekly health report    
    report = generate_report(csv_path)
    sent = send_msg_self(report)
    saving = store_weekly_report(date, report)
    if report == "Error: CSV file not found.":
        return report, 404

    return "Weekly report generated", 200

# ---------------------------- Call Handling
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from core.call_handler import call
from services.call import get_context, stt_engine, make_call
from setups import FROM, message_collection, twilio_client, NGROK_URL
active_calls = {}

@app.route('/voice', methods=["POST", "GET"])
def calling():
    """Handles incoming and outgoing calls using Twilio Media Streams."""
    print("Entered calling function in flask")
    response = VoiceResponse()
    call_id = request.form.get('CallSid', "")
    from_number = request.form.get('From', "")
    to_number = request.form.get('To', "")
    start_time = datetime.now().isoformat()
    call_type = request.args.get('type', None)

    response.say('Code execution started. Handling the call now.')
    number = from_number if from_number != FROM else to_number

    if call_id not in active_calls:
        active_calls[call_id] = {"context": get_context(number, message_collection)}

    ws_stream_url = f"wss://{request.host}/twilio-media-stream?call_id={call_id}&number={number}&start_time={start_time}&call_type={call_type}"
    print("Stream URL:" ,ws_stream_url)
    connect = Connect()
    stream = Stream(url=ws_stream_url)
    connect.append(stream)
    response.append(connect)
    
    return Response(str(response), content_type="application/xml")

@sock.route('/twilio-media-stream')
def handle_twilio_media_stream(ws):
    """Handles WebSocket connection for Twilio Media Streams."""
    query_params = request.args
    call_id = query_params.get("call_id", "")
    number = query_params.get("number", "")
    start_time = query_params.get("start_time", "")
    call_type = query_params.get("call_type", None)

    print("inside the /twilio-media-stream function now")
    context = active_calls.get(call_id, {}).get("context", "")

    while True:
        try:
            data = ws.receive()
            if not data:
                break
            data_json = json.loads(data)
            
            if data_json.get("event") == "media":
                # Process received audio payload (PCM format)
                audio_payload = data_json["media"]["payload"]
                raw_audio = base64.b64decode(audio_payload)
                # Use Deepgram to convert speech to text
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                user_text = loop.run_until_complete(stt_engine(raw_audio))
                print(f"User said: {user_text}")
                if not user_text or user_text.strip() == "":
                    user_text = "no input"
                # Generate AI response (TTS audio in PCM format)
                response_stream = call(call_id, number, start_time, context, user_text, call_type)
                for tts_chunk in response_stream:
                    ws.send(tts_chunk, binary=True)  # Stream PCM audio to Twilio

            elif data_json.get("event") == "stop":
                print(f"Call {call_id} ended. Cleaning up context.")
                active_calls.pop(call_id, None)
                break
        except Exception as e:
            print(f"WebSocket Error: {e}")
            break

@app.route('/initiate-call', methods=['GET'])
def initiate_call():
    """Trigger a Twilio call via a browser request."""
    client_number = os.getenv("CLIENT_NUMBER", "").split(":")[-1]
    if client_number:
        call_sid = make_call(client_number, twilio_client, NGROK_URL, "reminder")
        return jsonify({"message": "Outbound call initiated.", "call_sid": call_sid})
    return jsonify({"error": "Client number is missing."}), 400

# ---------------------------- Run Flask app
if __name__ == "__main__":    
    app.run(host="0.0.0.0", port=5000, debug=False)