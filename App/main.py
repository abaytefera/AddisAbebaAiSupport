from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import socketio


from App.routes import upload, chat, auth_routes, dashboard
from App.services.socket_manager import sio 


app = FastAPI(
    title="AI Assistant",
    description="Amharic & English AI Assistant",
    version="1.0"
)

# 2. Middleware 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Router-
app.include_router(upload.router, prefix='/upload', tags=['upload'])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(auth_routes.router, prefix="/auth", tags=["Authentication"])
app.include_router(dashboard.router, prefix='/analytics', tags=["dashboard"])

@app.get('/')
def root():
    return JSONResponse({
        "msg": "Welcome to Addis Ababa, Ethiopia"
    })


sio_app = socketio.ASGIApp(sio, other_asgi_app=app)