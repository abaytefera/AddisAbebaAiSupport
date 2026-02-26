import os
import time
from google import genai
from google.genai import types
from App.services.search_service import search_chunks

# Initialize client globally
# Ensure your .env has LLM_API_KEY
client = genai.Client(api_key=os.getenv("LLM_API_KEY"))

# 2026 Recommended Model Hierarchy
PRIMARY_MODEL = 'gemini-2.5-flash-lite' 
FALLBACK_MODEL = 'gemini-1.5-flash-8b' 

def generate_answer(question: str, top_k: int = 5, company_id: str = "") -> str:
    """
    Generates an answer using RAG logic with an automatic model fallback 
    to handle 429 Rate Limit errors.
    """
    try:
        # 1. RETRIEVAL: Get document chunks from pgvector
        chunks = search_chunks(question, top_k, company_id)
        if not chunks:
            return "I'm sorry, I couldn't find any documents related to your company to answer this."

        # Prepare context from retrieved chunks
        context_text = "\n\n".join([f"Source Document: {c.chunk_text}" for c in chunks])
     
        system_instruction = (
            "You are a professional AI Assistant. Answer strictly using the provided context. "
            "If the answer isn't in the context, politely say you don't know. "
            "Always match the user's language (Amharic or English)."
        )

        # 2. GENERATION: Attempt with Fallback Logic
        models_to_try = [PRIMARY_MODEL, FALLBACK_MODEL]
        last_error = ""

        for model_id in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_id,
                    contents=f"Context:\n{context_text}\n\nQuestion: {question}",
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.1,  # Keep it factual
                    )
                )
                
                if response and response.text:
                    return response.text
                
            except Exception as e:
                last_error = str(e)
                # If it's a 429 (Rate Limit), try the next model immediately
                if "429" in last_error:
                    print(f"⚠️ {model_id} rate limited. Trying fallback...")
                    continue 
                # If it's a different error, stop and report it
                break

        return f"AI Service is temporarily unavailable. (Detail: {last_error})"

    except Exception as e:
        return f"System Error: Please contact support. (Ref: {str(e)})"