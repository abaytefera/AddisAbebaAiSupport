from fastapi import APIRouter, HTTPException, status
from App.schemas.chat import ChatRequest, ChatResponse
from App.services.chat_service import generate_answer
from App.services.voice_service import process_voice_cloud, generate_voice_cloud

router = APIRouter()

@router.post("/", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest): 
    
    if not request.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="company_id is required for scoped search"
        )

    try:
        # --- CASE 1: TEXT ---
        if request.type == 'text':
            answer = generate_answer(
                question=request.message,
                top_k=request.top_k,
                company_id=request.company_id
            )
            return ChatResponse(
                answer=answer,
                type=request.type,
                role='assistant'
            )

        # --- CASE 2: VOICE ---
        elif request.type == 'voice':
            # 1. Cloud Speech-to-Text (Groq)
            print(request.audio_url)
            user_text, lang_code = await process_voice_cloud(request.audio_url)
            print(user_text)
            # Safety check: If STT failed
            if not user_text:
                user_text = "Empty audio"
            
            # 2. AI generates answer (Gemini/Llama)
            ai_answer = generate_answer(
                question=user_text,
                top_k=request.top_k,
                company_id=request.company_id
            )

            # 3. Handle Rate Limits/Empty AI Responses
            if not ai_answer or len(ai_answer.strip()) == 0:
                ai_answer = "I'm sorry, I am currently experiencing high traffic. Please try again soon."

            # 4. Generate Voice (Safe now because ai_answer is guaranteed to be a string)
            voice_url, duration = await generate_voice_cloud(ai_answer, lang_code)
            print(voice_url)

            return ChatResponse(
                answer=ai_answer,
                audio_url=voice_url,
                type=request.type,
                role='assistant',
                duration=duration
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported request type."
            )

    except Exception as e:
        print(f"Log Error: {e}") 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your chat request."
        )