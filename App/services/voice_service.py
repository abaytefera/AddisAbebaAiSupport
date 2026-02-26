import os
import requests
import cloudinary.uploader
import edge_tts
from groq import Groq
from tempfile import NamedTemporaryFile
from mutagen.mp3 import MP3

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# 1. Improved Transcription (የተሻሻለ የድምፅ ፍተሻ)
async def process_voice_cloud(audio_url: str):
    response = requests.get(audio_url)
    with NamedTemporaryFile(delete=False, suffix=".m4a") as temp_audio:
        temp_audio.write(response.content)
        temp_path = temp_audio.name
    try:
        with open(temp_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(temp_path, file.read()),
                model="whisper-large-v3",
                # The prompt below stops the "Arabic" mistake
                prompt="This is a conversation in Amharic and English. አማርኛ እና እንግሊዝኛ።",
                response_format="verbose_json",
            )
        
        # Detected language (e.g., 'am' or 'en')
        detected_lang = transcription.language
        return transcription.text, detected_lang
    finally:
        os.remove(temp_path)

# 2. Adaptive Voice Response (እንደ ቋንቋው የሚቀያየር ድምፅ)
async def generate_voice_cloud(text: str, lang_code: str):
    # Map detected language to the correct AI voice
    voice_map = {
        "am": "am-ET-AmeleNeural",    # Amharic Voice
        "en": "en-US-AndrewNeural",   # English Voice
    }
    
    # If it detects something else, default to English
    selected_voice = voice_map.get(lang_code, "en-US-AndrewNeural")

    with NamedTemporaryFile(delete=False, suffix=".mp3") as temp_mp3:
        communicate = edge_tts.Communicate(text, selected_voice)
        await communicate.save(temp_mp3.name)
        
        audio = MP3(temp_mp3.name)
        duration = audio.info.length

        upload_result = cloudinary.uploader.upload(
            temp_mp3.name, 
            resource_type="video",
            folder="ai_voice_responses"
        )
        return upload_result['secure_url'], duration