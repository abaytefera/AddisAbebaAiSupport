from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text  
from App.routes import upload, chat,auth_routes,dashboard
from App.database.connection import engine, Base
from App.models.model import DocumentChunk
import socketio
from App.services.socket_manager import sio # We will create this file



app = FastAPI(
    title="AI Assistant",
    description="Amharic & English AI Assistant",
    version="1.0"
)
sio_app = socketio.ASGIApp(sio, other_asgi_app=app)


sio_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sio_app.include_router(upload.router, prefix='/upload', tags=['upload'])
sio_app.include_router(chat.router, prefix="/chat", tags=["chat"])
sio_app.include_router(auth_routes.router, prefix="/auth", tags=["Authentication"])

sio_app.include_router(dashboard.router,prefix='/analytics',tags=["dashboard"])


@sio_app.get('/')
def root():
    return JSONResponse({
        "msg": "welcome to ethiopian addis abeba"
    })
