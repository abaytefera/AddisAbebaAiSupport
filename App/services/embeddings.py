import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
# MUST be this model to match your 768-dimension database
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

# FIXED: 2026 Unified Router URL for models
API_URL = f"https://router.huggingface.co/hf-inference/models/{EMBED_MODEL}/pipeline/feature-extraction"

def create_embedding(text: str) -> list:
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    # The 2026 router expects 'inputs' for the feature-extraction pipeline
    payload = {"inputs": text}
    
    for attempt in range(3):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                # Feature extraction returns a nested list: [[dim1, dim2, ...]]
                # We need to flatten it to [dim1, dim2, ...]
                return result[0] if isinstance(result[0], list) else result
            
            if response.status_code == 410:
                # This should not happen with the new URL, but added for safety
                print("Endpoint deprecated. Check API_URL.")
                break
                
            print(f"Embedding Error: {response.status_code} - {response.text}")
            time.sleep(2)
        except Exception as e:
            print(f"Connection Error: {e}")
            time.sleep(2)
            
    return [0.0] * 768  # Return 768 zeros so the SQL doesn't crash