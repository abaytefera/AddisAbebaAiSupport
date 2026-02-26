import os
import time
from google import genai
from google.genai import types
from App.services.search_service import search_chunks

# Initialize client with v1 to ensure stability in 2026
client = genai.Client(
    api_key=os.getenv("LLM_API_KEY"),
    http_options=types.HttpOptions(api_version='v1')
)

# 2026 Optimized Model Hierarchy
PRIMARY_MODEL = 'gemini-2.5-flash'      
FALLBACK_MODEL = 'gemini-2.5-flash-lite'

def generate_answer(question: str, top_k: int = 5, company_id: str = "") -> str:
    """
    Generates a direct answer using RAG logic. 
    Handles greetings, removes boilerplate, and fixes newline escaping.
    """
    try:
        # 1. RETRIEVAL
        chunks = search_chunks(question, top_k, company_id)
        if not chunks:
            # Check if the question is just a greeting even without chunks
            if any(greet in question.lower() for greet in ["hello", "hi", "ሰላም"]):
                return "ሰላም! እንዴት ልረዳዎት እችላለሁ? (Hello! How can I help you?)"
            return "I'm sorry, I couldn't find any documents related to your company to answer this."

        context_text = "\n\n".join([f"Source Document: {c.chunk_text}" for c in chunks])
     
        # Hierarchical Instructions: Allows for greetings + strict context use
        full_prompt = (
            f"SYSTEM INSTRUCTIONS:\n"
            f"1. If the user greets you (e.g., 'Hello', 'ሰላም'), greet them back naturally.\n"
            f"2. For the main answer, use ONLY the provided context. Do not make up facts.\n"
            f"3. Do not use formal intros like 'Based on the context'.\n"
            f"4. Give the answer immediately. If the answer isn't in the context, say you don't know.\n"
            f"5. Always match the user's language (Amharic or English).\n\n"
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
                    config=types.GenerateContentConfig(
                        temperature=0.3, # Balanced for natural greetings + factual accuracy
                    )
                )
                
                if response and response.text:
                    # Normalizes literal \n characters to real line breaks for UI rendering
                    return response.text.replace("\\n", "\n").strip()
                
            except Exception as e:
                last_error = str(e)
                # Retry on specific transient/name errors
                if any(err_code in last_error for err_code in ["429", "404", "400"]):
                    print(f"⚠️ {model_id} issue. Trying fallback...")
                    time.sleep(2)
                    continue 
                break 

        return f"AI Service is temporarily unavailable. (Detail: {last_error})"

    except Exception as e:
        return f"System Error: Please contact support. (Ref: {str(e)})"