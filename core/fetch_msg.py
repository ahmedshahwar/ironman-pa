import time
from pathlib import Path

from services.dnt_vns import download_media, transcribe_audio

# ---------------------------- VNs setup
VOICE_NOTES_DIR = Path("voice_notes")

def fetch_msg(request_data):
    """Processes an incoming WhatsApp message, including media handling."""
    
    message_id = request_data.get('MessageSid', '')
    sender = request_data.get('From', '')
    incoming_msg = request_data.get('Body', '')
    num_media = int(request_data.get('NumMedia', 0))

    message_data = {
        "message_id": message_id,
        "sender": sender,
        "message": incoming_msg,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "media_urls": [],
        "processed": False,
    }

    # Handle voice notes
    if num_media > 0:
        for i in range(num_media):
            media_url = request_data.get(f"MediaUrl{i}")
            media_type = request_data.get(f"MediaContentType{i}", "")

            if media_type.startswith("audio/"):
                VOICE_NOTES_DIR.mkdir(exist_ok=True)
                file_name = f"{message_id}_{i}.ogg"
                file_path = VOICE_NOTES_DIR / file_name

                if download_media(media_url, file_path):
                    transcribed_text = transcribe_audio(file_path)
                    message_data["message"] = transcribed_text
                    message_data["media_urls"].append(str(file_path))

    print(f""" Message from Fetch_MSG module:
    =========================================
    Message ID: {message_data['message_id']}
    Sender: {message_data['sender']}
    Message: {message_data['message']}
    Timestamp: {message_data.get('timestamp', 'N/A')}
    Media URLs: {', '.join(message_data['media_urls']) if message_data['media_urls'] else 'None'}
    =========================================
    """)

    return message_data