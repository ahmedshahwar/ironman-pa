import requests
from pydub import AudioSegment
import speech_recognition as sr

from setups import account_sid, auth_token

# ---------------------------- Download VNs and transcribe them
def download_media(media_url, file_path):
    from requests.auth import HTTPBasicAuth
    try:
        response = requests.get(media_url, auth=HTTPBasicAuth(account_sid, auth_token), timeout=10)
        response.raise_for_status() 
        with open(file_path, "wb") as f:
            f.write(response.content)
        print(f"Downloaded media: {file_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to download media: {e}")
        return False


def transcribe_audio(file_path):
    try:
        wav_file_path = file_path.with_suffix(".wav")
        audio = AudioSegment.from_file(file_path, format="ogg")
        audio.export(wav_file_path, format="wav")

        recognizer = sr.Recognizer()

        # Load audio file
        with sr.AudioFile(str(wav_file_path)) as source:
            audio_data = recognizer.record(source)

        # Use Google Web Speech API (No API key required)
        transcribed_text = recognizer.recognize_google(audio_data)

        # Delete the files after processing
        file_path.unlink()
        wav_file_path.unlink()

        return transcribed_text.strip()

    except sr.UnknownValueError:
        return "Could not understand audio"
    except sr.RequestError:
        return "API request failed"
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return "Transcription error"
