import socketio

# 1. Socket server መፍጠር
sio = socketio.AsyncServer(
    async_mode='asgi', 
    cors_allowed_origins='*',
    ping_timeout=60,
    ping_interval=25
)

# 2. ይህንን 'sio_app' ነው Render ላይ የምታስነሳው
sio_app = socketio.ASGIApp(sio)

@sio.event
async def connect(sid, environ, auth=None): # <--- 'auth' እዚህ ጋር መጨመሩ ወሳኝ ነው
    print(f"🚀 Connected: {sid}")
    if auth:
        print(f"User Auth Data: {auth}")

@sio.on("join_chat")
async def join_chat(sid, data):
    session_id = data.get('session_id')
    if session_id:
        # 1. Join the room
        await sio.enter_room(sid, str(session_id))
        print(f"✅ SID {sid} joined room: {session_id}")
        
        # 2. Send confirmation ONLY to the user who joined
        await sio.emit("joined_success", {"status": "ok"}, to=sid)

@sio.event
async def disconnect(sid):
    print(f"❌ Disconnected: {sid}")