import os
import random
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import socketio
import cv_logic

app = FastAPI()
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio, app)

rooms = {}

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
    for code, room in list(rooms.items()):
        if room.get('pc_sid') == sid or room.get('mobile_sid') == sid:
            other_sid = room.get('mobile_sid') if room.get('pc_sid') == sid else room.get('pc_sid')
            if other_sid:
                await sio.emit('partner_disconnected', room=other_sid)
            del rooms[code]
            break

@sio.event
async def create_room(sid):
    code = str(random.randint(1000, 9999))
    while code in rooms:
        code = str(random.randint(1000, 9999))
    
    rooms[code] = {
        'pc_sid': sid,
        'mobile_sid': None,
        'game': cv_logic.ChessGameTracker()
    }
    await sio.emit('room_created', {'code': code}, room=sid)

@sio.event
async def join_room(sid, data):
    code = data.get('code')
    if code in rooms and rooms[code].get('mobile_sid') is None:
        rooms[code]['mobile_sid'] = sid
        await sio.emit('room_joined', {'success': True}, room=sid)
        await sio.emit('mobile_connected', room=rooms[code]['pc_sid'])
    else:
        await sio.emit('room_joined', {'success': False, 'message': 'Invalid code or room full'}, room=sid)

@sio.event
async def start_game(sid, data):
    code = data.get('code')
    if code in rooms and rooms[code].get('pc_sid') == sid:
        # PC started the game
        await sio.emit('game_started', room=rooms[code]['mobile_sid'])

@sio.event
async def set_corners(sid, data):
    code = data.get('code')
    corners = data.get('corners')
    import numpy as np
    if code in rooms and rooms[code].get('mobile_sid') == sid:
        room = rooms[code]
        game_tracker = room['game']
        game_tracker.board_corners = np.array(corners, dtype="float32")
        game_tracker.prev_board_img = None # Reset baseline
        game_tracker.auto_orientation = None

@sio.event
async def reset_game(sid, data):
    code = data.get('code')
    if code in rooms and rooms[code].get('mobile_sid') == sid:
        import chess
        rooms[code]['game'].board = chess.Board()
        rooms[code]['game'].prev_board_img = None
        rooms[code]['game'].error_count = 0
        await sio.emit('scan_error', {'message': 'Game reset to starting position.'}, room=sid)

@sio.event
async def send_frame(sid, data):
    # Mobile sends a frame
    code = data.get('code')
    image_data = data.get('image') # Base64 encoded image or raw bytes
    
    if code in rooms and rooms[code].get('mobile_sid') == sid:
        room = rooms[code]
        game_tracker = room['game']
        
        # Process frame
        orientation = data.get('orientation', 'auto')
        border_inset = data.get('border_inset', '0')
        result = game_tracker.process_frame(image_data, orientation=orientation, border_inset=border_inset)
        
        if result.get("error"):
            await sio.emit('scan_error', result, room=sid)
        elif result.get("no_change"):
            await sio.emit('scan_no_change', result, room=sid)
        elif result.get("moved"):
            # Send move to PC
            await sio.emit('move_detected', result, room=room['pc_sid'])
            # Send ack to Mobile
            await sio.emit('scan_success', result, room=sid)

# Serve static files for frontend
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Serve index.html for all other paths to support React Router
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Frontend build not found."}

if __name__ == "__main__":
    uvicorn.run("main:socket_app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
