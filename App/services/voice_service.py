import os
import requests
import cloudinary.uploader
import edge_tts
from groq import Groq
from tempfile import NamedTemporaryFile
from mutagen.mp3 import MP3




import assemblyai as aai

# 1. API Key from your .env
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")

async def process_voice_cloud(audio_url: str):
    """
    Transcribes Amharic using the required 2026 AssemblyAI multi-model parameter.
    """
    try:
        # FIX: 'speech_models' is now REQUIRED and must be a LIST of strings.
        # We use ['universal-3-pro', 'universal-2'] for the highest Amharic accuracy.
        config = aai.TranscriptionConfig(
            language_code="am", 
            speech_models=["universal-3-pro", "universal-2"] 
        )

        # Use the standard Transcriber (NOT AsyncTranscriber)
        transcriber = aai.Transcriber()
        
        # .transcribe() manages the polling/waiting for the URL result automatically.
        transcript = transcriber.transcribe(audio_url, config=config)

        # Handle potential errors
        if transcript.status == aai.TranscriptStatus.error:
            print(f"AssemblyAI Error: {transcript.error}")
            return None, "error"

        # Return the Ge'ez text and language code
        return transcript.text, "am"

    except Exception as e:
        print(f"Unexpected Error: {e}")
        return None, "error"
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