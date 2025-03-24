from datetime import datetime, timedelta
import json, dateparser, io, base64, asyncio
from setups import FROM, DEEPGRAM_API
import soundfile as sf
from pydub import AudioSegment
from deepgram import DeepgramClient

deepgram = DeepgramClient(DEEPGRAM_API)

""" 
    This file contains all the HELPER FUNCTIONS for call handling.
"""

def check_intent(conv_hist, call_id, LLM):
    """
    Determines the caller's intent based on the conversation history. Classifies the intent into one of the following categories:
        1. schedule_appt
        2. reschedule_appt
        3. cancel_appt
        4. none
    """
    with open(r"prompts/check_intent.txt", 'r') as f:
        prompt = f.read().strip()
    
    conversation_history = "\n".join([f"{entry['role']}: {entry['content']}" for entry in conv_hist.get(call_id, [])])
    prompt = prompt.replace("{convo}", conversation_history)

    response = LLM.invoke(prompt)
    try:
        result = json.loads(response.content)
        return result 
    except Exception as e:
        print(f"Error extracting intent: {e}")
        return None
    
def extract_details(conv_hist, call_id, LLM, task=None):
    """
    Extracts specific details related to a task from the conversation history and event description.
    """
    with open(r"prompts/task_extraction.txt", 'r') as f:
        extraction_prompt = f.read().strip()

    conversation_history = "\n".join([f"{entry['role']}: {entry['content']}" for entry in conv_hist.get(call_id, [])])
    task_details = ""
    if task:
        description = task.get("description", "")
        for line in description.split("\n"):
            if not line.startswith("Task"):
                task_details += line + "\n"
        task_details += f"When: {task.get('time', 'No Time')}\n"

    else:
        task_details = "No previous task details available."

    extraction_prompt = extraction_prompt.replace("{convo}", conversation_history)
    extraction_prompt = extraction_prompt.replace("{task_details}", task_details)

    response = LLM.invoke(extraction_prompt)
    try:
        extracted_details = json.loads(response.content)
        return extracted_details
    except Exception as e:
        print(f"Error extracting intent: {e}")
        return None


def make_call(to_num, client, url, type=None):
    """Initializes call to a given number using Twilio."""
    try:
        call = client.calls.create(
            url=f"{url}/voice?type={type if type else ""}",
            to=to_num,
            from_=FROM,
        )
        return call.sid
    except Exception as e:
        print("Error initializing call:", e)
        return {"error": "Call not initialized"}

def get_context(number, collection):
    """Extracts the last 7 days conversation from WhatsApp messages."""
    last_week = datetime.now() - timedelta(days=7)
    last_week = last_week.strftime("%Y-%m-%d %H:%M:%S")

    messages = list(collection.find({
        "sender": f"whatsapp:{number}",
        "timestamp": {"$gte": last_week}
    }))
    context = '\n'.join([msg['message'] for msg in messages])
    return context

def extract_time(text):
    """Extracts a datetime object from user input."""
    try:
        parsed_time = dateparser.parse(text, settings={'PREFER_DATES_FROM': 'future'})
        return parsed_time if parsed_time else None
    except Exception as e:
        print(f"Error extracting time: {e}")
        return None

def generate_call_summary(conversation, call_id, number, call_type, start_time, LLM):
    """Generates call summary using OpenAI."""
    
    with open(r"prompts/call_summary.txt", 'r') as f:
        prompt = f.read().strip()
    prompt = prompt.replace("{convo}", conversation)

    response = LLM.invoke(prompt)
    try:
        summary_data = json.loads(response.content)
    except Exception as e:
        print(f"Error parsing AI response: {e}")
        summary_data = {"summary": "Unable to generate summary", "callback_req": "no"}
    
    summary_data["call_id"] = call_id
    summary_data["call_type"] = call_type
    summary_data["number"] = number
    summary_data["timestamp"] = start_time

    return summary_data

def tts_engine(text, client):
    """Converts text to speech using OpenAI TTS API."""
    response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text,
        response_format="mp3",
    )
    return to_pcm(response.content)
    # return response.content

async def stt_engine(pcm_audio):
    """Transcribe PCM audio using Deepgram's WebSocket API."""
    try:
        deepgram_live = await deepgram.transcription.live({
            'encoding': 'linear16',
            'sample_rate': 8000,
            'channels': 1,
            'interim_results': True,
            'punctuate': True,
        })

        transcript = ""
        async def process_transcription():
            async for result in deepgram_live:
                if "channel" in result:
                    transcript = result["channel"]["alternatives"][0]["transcript"]
                    print(f"Interim Transcript: {transcript}")
        
        asyncio.create_task(process_transcription())
        await deepgram_live.send(pcm_audio)
        return transcript

    except Exception as e:
        print(f"Deepgram Error: {e}")
        return ""
    
def to_wav(pcm_audio):
    """Convert PCM (μ-law) audio to 16-bit WAV for Whisper STT."""
    audio = AudioSegment(
        data=pcm_audio,
        sample_width=1,  # μ-law is 8-bit
        frame_rate=8000,
        channels=1
    )
    audio = audio.set_sample_width(2)  # Convert to 16-bit PCM
    wav_io = io.BytesIO()
    audio.export(wav_io, format="wav")
    return wav_io.getvalue()  # Return WAV as bytes


def to_pcm(tts_audio):
    """Convert MP3 TTS response to PCM for Twilio streaming."""
    audio = AudioSegment.from_file(io.BytesIO(tts_audio), format="mp3")
    audio = audio.set_frame_rate(8000).set_channels(1)
    pcm_io = io.BytesIO()
    audio.export(pcm_io, format="s16le")
    return pcm_io.getvalue()