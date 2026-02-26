from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text  
from App.routes import upload, chat,auth_routes
from App.database.connection import engine, Base
from App.models.model import DocumentChunk




app = FastAPI(
    title="AI Assistant",
    description="Amharic & English AI Assistant",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix='/upload', tags=['upload'])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(auth_routes.router, prefix="/auth", tags=["Authentication"])

@app.get('/')
def root():
    return JSONResponse({
        "msg": "welcome to ethiopian addis abeba"
    })
