from datetime import datetime, timedelta
import json, dateparser,asyncio
from setups import FROM, DEEPGRAM_API
from deepgram import DeepgramClient, SpeakWebSocketEvents, SpeakWSOptions

deepgram = DeepgramClient(DEEPGRAM_API)

with open(r"prompts/check_intent.txt", 'r') as f:
    INTENT_PROMPT = f.read().strip()

with open(r"prompts/task_extraction.txt", 'r') as f:
    EXTRACTION_PROMPT = f.read().strip()

def check_intent(conv_hist, call_id, LLM):
    conversation_history = "\n".join([f"{entry['role']}: {entry['content']}" for entry in conv_hist.get(call_id, [])])
    prompt = INTENT_PROMPT.replace("{convo}", conversation_history)

    response = LLM.invoke(prompt)
    try:
        result = json.loads(response.content)
        return result 
    except Exception as e:
        print(f"Error extracting intent: {e}")
        return None
    
def extract_details(conv_hist, call_id, LLM, task=None):
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
    
    extraction_prompt = EXTRACTION_PROMPT.replace("{current_date}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
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
    last_week = datetime.now() - timedelta(days=7)
    last_week = last_week.strftime("%Y-%m-%d %H:%M:%S")

    messages = list(collection.find({
        "sender": f"whatsapp:{number}",
        "timestamp": {"$gte": last_week}
    }))
    context = '\n'.join([msg['message'] for msg in messages])
    return context

def extract_time(text):
    try:
        parsed_time = dateparser.parse(text, settings={'PREFER_DATES_FROM': 'future'})
        return parsed_time if parsed_time else None
    except Exception as e:
        print(f"Error extracting time: {e}")
        return None

def generate_call_summary(conversation, call_id, number, call_type, start_time, LLM):    
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

async def tts_engine(text):
    """Converts text to speech using Deepgram's TTS API."""
    dg_connection = deepgram.speak.websocket.v('1')

    options = SpeakWSOptions(
        model="aura-luna-en",
        encoding='linear16',
        sample_rate=8000
    )

    audio_data = []
    
    def on_binary_data(self, data, **kwargs):
        audio_data.append(data)
        
    dg_connection.on(SpeakWebSocketEvents.AudioData, on_binary_data)

    if not dg_connection.start(options):
        print("[ERROR] Failed to start Deepgram WebSocket connection.")
        return None

    dg_connection.send_text(text)
    dg_connection.flush()
    await dg_connection.wait_for_event(SpeakWebSocketEvents.Close)
    dg_connection.finish()

    tts_audio = b''.join(audio_data)
    return tts_audio

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
        async def get_transcript():
            nonlocal transcript
            async for result in deepgram_live:
                if "channel" in result:
                    transcript = result["channel"]["alternatives"][0]["transcript"]
        
        # Wait for both sending and receiving
        await asyncio.gather(
            deepgram_live.send(pcm_audio),
            get_transcript()
        )
        return transcript
    except Exception as e:
        print(f"Deepgram Error: {e}")
        return ""


# def tts_engine(text, client):
#     """Converts text to speech using OpenAI TTS API."""
#     response = client.audio.speech.create(
#         model="tts-1",
#         voice="nova",
#         input=text,
#         response_format="mp3",
#     )
#     return to_pcm(response.content)
#     # return response.content


# def to_wav(pcm_audio):
#     """Convert PCM (μ-law) audio to 16-bit WAV for Whisper STT."""
#     audio = AudioSegment(
#         data=pcm_audio,
#         sample_width=1,  # μ-law is 8-bit
#         frame_rate=8000,
#         channels=1
#     )
#     audio = audio.set_sample_width(2)  # Convert to 16-bit PCM
#     wav_io = io.BytesIO()
#     audio.export(wav_io, format="wav")
#     return wav_io.getvalue()  # Return WAV as bytes


# def to_pcm(tts_audio):
#     """Convert MP3 TTS response to PCM for Twilio streaming."""
#     audio = AudioSegment.from_file(io.BytesIO(tts_audio), format="wav")
#     print(f"Audio type [LINE 211]: {type(audio)}")  
#     audio = audio.set_frame_rate(8000).set_channels(1).set_sample_width(2)
#     pcm_io = io.BytesIO()
#     audio.export(pcm_io, format="s16le")
#     return pcm_io.getvalue()