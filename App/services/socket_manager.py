import socketio

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

@sio.event
async def connect(sid, environ):
    print(f"Connected: {sid}")

@sio.on("join_chat")
async def join_chat(sid, data):
    # data: {"session_id": "..."}
    # Join a room specific to this chat session
    await sio.enter_room(sid, data['session_id'])

@sio.event
async def disconnect(sid):
    print(f"Disconnected: {sid}")