import os
import requests
import cloudinary.uploader
import edge_tts
from groq import Groq
from tempfile import NamedTemporaryFile
from mutagen.mp3 import MP3

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# 1. Improved Transcription with "Amharic Protection"
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
                # Hard-coding 'am' is the ONLY way to ensure 100% Amharic detection
                language="am", 
                prompt="አማርኛ ንግግር። This is Amharic and English speech.",
                response_format="verbose_json",
            )
        
        detected_lang = transcription.language
        
        # Whisper Fix: If it guesses Arabic, it's almost certainly Amharic
        if detected_lang == "ar":
            detected_lang = "am"
            
        return transcription.text, detected_lang
    finally:
        os.remove(temp_path)

# 2. Adaptive Voice Response with Ge'ez Detection
async def generate_voice_cloud(text: str, lang_code: str):
    # Updated Voice Map for Edge-TTS
    voice_map = {
        "am": "am-ET-MekdesNeural",   # Standard Female Amharic
        "en": "en-US-AndrewNeural",   # Standard Male English
    }
    
    # SAFETY CHECK: If the text contains Ge'ez characters, force Amharic voice
    # This prevents the AI from speaking Amharic text with an English accent
    is_geez = any('\u1200' <= char <= '\u137F' for char in text)
    
    if is_geez:
        selected_voice = "am-ET-MekdesNeural"
    else:
        selected_voice = voice_map.get(lang_code, "en-US-AndrewNeural")

    with NamedTemporaryFile(delete=False, suffix=".mp3") as temp_mp3:
        communicate = edge_tts.Communicate(text, selected_voice)
        await communicate.save(temp_mp3.name)
        
        audio = MP3(temp_mp3.name)
        duration = audio.info.length

        upload_result = cloudinary.uploader.upload(
            temp_mp3.name, 
            resource_type="auto", # Use 'auto' instead of 'video'
            folder="ai_voice_responses"
        )
        return upload_result['secure_url'], duration