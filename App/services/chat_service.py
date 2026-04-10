import os
import time
import re
from google import genai
from google.genai import types
from App.services.search_service import search_chunks

# Initialize client with v1 to ensure stability in 2026
client = genai.Client(
    api_key=os.getenv("LLM_API_KEY"),
    http_options=types.HttpOptions(api_version='v1')
)

PRIMARY_MODEL = 'gemini-2.5-flash'      
FALLBACK_MODEL = 'gemini-2.5-flash-lite'

def is_amharic(text: str) -> bool:
    """ጥያቄው ውስጥ የአማርኛ ፊደላት መኖራቸውን ያረጋግጣል"""
    # Unicode range for Ethiopic (Amharic)
    return bool(re.search(r'[\u1200-\u137F]', text))

def generate_answer(question: str, top_k: int = 5, company_id: str = "") -> str:
    # ቋንቋውን መለየት
    user_lang_am = is_amharic(question)

    try:
        # 1. RETRIEVAL
        chunks = search_chunks(question, top_k, company_id)
        if not chunks:
            if any(greet in question.lower() for greet in ["hello", "hi", "ሰላም"]):
                return "ሰላም! እንዴት ልረዳዎት እችላለሁ?" if user_lang_am else "Hello! How can I help you?"
            
            return "ይቅርታ፣ ከድርጅትዎ መረጃ ጋር የተያያዘ መልስ ማግኘት አልቻልኩም።" if user_lang_am else \
                   "I'm sorry, I couldn't find any documents related to your company to answer this."

        context_text = "\n\n".join([f"Source Document: {c.chunk_text}" for c in chunks])
     
        full_prompt = (
            f"SYSTEM INSTRUCTIONS:\n"
            f"1. If the user greets you, greet them back naturally.\n"
            f"2. Use ONLY the provided context. Do not make up facts.\n"
            f"3. Do not use formal intros like 'Based on the context'.\n"
            f"4. Match the user's language (Amharic or English).\n\n"
            f"CONTEXT:\n{context_text}\n\n"
            f"USER QUESTION: {question}"
        )

        # 2. GENERATION: Attempt with Fallback Logic
        models_to_try = [PRIMARY_MODEL, FALLBACK_MODEL]
        last_error = ""

        for model_id in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_id,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(temperature=0.3)
                )
                
                if response and response.text:
                    return response.text.replace("\\n", "\n").strip()
                
            except Exception as e:
                last_error = str(e).upper()
                # 503 እና UNAVAILABLE እዚህ ተጨምረዋል
                if any(err in last_error for err in ["429", "404", "400", "503", "UNAVAILABLE"]):
                    print(f"⚠️ {model_id} issue. Trying next...")
                    time.sleep(1.5)
                    continue 
                break 

        # --- በቋንቋው መሰረት የሚመለስ ስህተት ---
        if user_lang_am:
            return "ይቅርታ፣ በአሁኑ ሰዓት ሰርቨሩ ስራ በዝቶበታል። እባክዎን ጥቂት ቆይተው ይሞክሩ።"
        return "I'm sorry, the AI service is currently overloaded. Please try again in a moment."

    except Exception as e:
        print(f"System Error: {e}")
        if user_lang_am:
            return "ይቅርታ፣ ሲስተም ላይ ስህተት ተከስቷል። እባክዎን የቴክኒክ ድጋፍ ያግኙ።"
        return "System Error: Please contact support regarding this issue."