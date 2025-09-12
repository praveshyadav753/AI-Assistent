from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import threading
import json
from typing import List

import time

# Import your working voice function and shared flag
from main import handle_voice_command, direct_wakeup_flag

# FastAPI app
app = FastAPI()

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global thread reference
voice_thread = None
connected_websockets: List[WebSocket] = []

@app.on_event("startup")
async def startup_event():
    """Start voice assistant when FastAPI starts"""
    global voice_thread
    print("[INFO] Starting voice assistant thread...")

    # Single thread for voice assistant
    voice_thread = threading.Thread(
        target=handle_voice_command,
        daemon=True,
        name="VoiceAssistant"
    )
    voice_thread.start()

    time.sleep(1)
    if voice_thread.is_alive():
        print(f"[SUCCESS] Voice assistant started - Thread ID: {voice_thread.ident}")
    else:
        print("[ERROR] Voice assistant thread failed to start!")


async def broadcast_message(msg_type: str, message: str = ""):
    payload = json.dumps({"type": msg_type, "message": message})
    for ws in connected_websockets:
        try:
            await ws.send_text(payload)
        except:
            # Ignore broken connections
            pass
        
@app.get("/")
def root():
    return {"message": "Voice Assistant API is running"}


@app.get("/api/status")
def get_status():
    """Check voice assistant status"""
    global voice_thread
    if voice_thread is None:
        return {
            "voice_assistant_running": False,
            "status": "not_started",
            "message": "Voice assistant thread not created"
        }

    is_alive = voice_thread.is_alive()
    return {
        "voice_assistant_running": is_alive,
        "status": "running" if is_alive else "stopped",
        "thread_name": voice_thread.name if voice_thread else None,
        "message": f"Voice assistant is {'running' if is_alive else 'stopped'}"
    }


@app.post("/start-wakeup/")
async def start_wakeup():
    """Trigger direct wakeup without creating a new thread"""
    # Set the flag so the existing thread skips wake word detection
    direct_wakeup_flag.set()
    await broadcast_message("direct_wakeup", "Direct wakeup triggered")
    return {"status": "success", "message": "Direct wakeup triggered"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connected")

    # Add websocket to the list
    connected_websockets.append(websocket)

    try:
        global voice_thread
        voice_running = voice_thread.is_alive() if voice_thread else False

        await websocket.send_text(json.dumps({
            "type": "initial_state",
            "message": "Connected to voice assistant",
            "voice_assistant_running": voice_running
        }))

        while True:
            data = await websocket.receive_text()
            # Optional: handle commands from frontend
            await websocket.send_text(json.dumps({
                "type": "received",
                "message": "Message received"
            }))

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    finally:
        # Remove disconnected websocket
        connected_websockets.remove(websocket)



if __name__ == "__main__":
    import uvicorn
    print("[INFO] Starting FastAPI server...")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
