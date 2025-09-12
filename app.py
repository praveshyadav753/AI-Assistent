from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import threading
import json
import asyncio
from typing import List
import time

from main import handle_voice_command, direct_wakeup_flag

app = FastAPI()

# --- START: ADD THESE MISSING DEFINITIONS ---

class AssistantState:
    """A simple class to hold the assistant's state."""
    def __init__(self):
        self.is_awake = False
        self.is_listening = False
        self.is_speaking = False
        self.current_command = ""
        self.current_response = ""
        self.message = "Initializing..."

    def to_dict(self):
        return self.__dict__

# Create the global state object and main event loop variable
assistant_state = AssistantState()
main_loop = None 

# --- END: ADD THESE MISSING DEFINITIONS ---


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

voice_thread = None
connected_websockets: List[WebSocket] = []

@app.on_event("startup")
async def startup_event():
    """Start voice assistant when FastAPI starts"""
    global voice_thread, main_loop
    
    # --- ADD THIS LINE ---
    # Get the main asyncio event loop so the background thread can use it
    main_loop = asyncio.get_running_loop()
    
    print("[INFO] Starting voice assistant thread...")

    voice_thread = threading.Thread(
        target=handle_voice_command,
        args=(send_update_to_clients,),
        daemon=True,
        name="VoiceAssistant"
    )
    voice_thread.start()

    time.sleep(1)
    if voice_thread.is_alive():
        print(f"[SUCCESS] Voice assistant started - Thread ID: {voice_thread.ident}")
    else:
        print("[ERROR] Voice assistant thread failed to start!")

# --- START: FIX THIS BROADCAST FUNCTION ---

async def broadcast_message(payload: dict):
    """
    Broadcasts a full JSON payload to all connected WebSocket clients.
    """
    for ws in connected_websockets:
        try:
            # Use send_json to send the dictionary directly
            await ws.send_json(payload)
        except Exception:
            # Ignore broken connections
            pass

# --- END: FIX THIS BROADCAST FUNCTION ---


def send_update_to_clients(event_type: str, data: dict = None):
    """
    This function is called FROM the voice assistant thread.
    It safely schedules the async broadcast function to run on the main FastAPI event loop.
    """
    global main_loop, assistant_state
    if not data:
        data = {}

    # (This state update logic is correct)
    if event_type == "status_update":
        assistant_state.message = data.get("message", assistant_state.message)
        if "Waiting for wake word" in assistant_state.message:
            assistant_state.is_awake = False
            assistant_state.is_listening = False
            assistant_state.is_speaking = False
            assistant_state.current_command = ""
            assistant_state.current_response = ""
    elif event_type == "wake_word_detected":
        assistant_state.is_awake = True
        assistant_state.message = "Wake word detected!"
    elif event_type == "listening_started":
        assistant_state.is_listening = True
        assistant_state.is_awake = True
        assistant_state.message = "Listening for your command..."
        assistant_state.current_command = ""
        assistant_state.current_response = ""
    elif event_type == "command_recognized":
        assistant_state.is_listening = False
        assistant_state.current_command = data.get("command", "")
        assistant_state.message = "Processing your command..."
    elif event_type == "response_generated":
        assistant_state.is_speaking = True
        assistant_state.is_awake = False
        assistant_state.current_response = data.get("response", "")
        assistant_state.message = "Generating response..."
    elif event_type == "speaking_finished":
        assistant_state.is_speaking = False
        assistant_state.message = "Finished speaking."

    payload = {
        "type": event_type,
        "data": data,
        "assistant_state": assistant_state.to_dict()
    }
    
    if main_loop and main_loop.is_running():
        # This call now correctly matches the new broadcast_message function
        asyncio.run_coroutine_threadsafe(broadcast_message(payload), main_loop)

# (The rest of your file is correct, no changes needed below this point)
@app.get("/")
def root():
    return {"message": "Voice Assistant API is running"}

@app.get("/api/status")
def get_status():
    global voice_thread
    if voice_thread is None:
        return {"voice_assistant_running": False, "status": "not_started"}
    is_alive = voice_thread.is_alive()
    return {
        "voice_assistant_running": is_alive,
        "status": "running" if is_alive else "stopped",
        "assistant_state": assistant_state.to_dict()
    }

@app.post("/start-wakeup/")
async def start_wakeup():
    direct_wakeup_flag.set()
    send_update_to_clients("direct_wakeup", {"message": "Direct wakeup triggered"})
    return {"status": "success", "message": "Direct wakeup triggered"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connected")
    connected_websockets.append(websocket)
    try:
        initial_payload = {
            "type": "initial_state",
            "message": "Connected to voice assistant",
            "assistant_state": assistant_state.to_dict()
        }
        await websocket.send_json(initial_payload)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    finally:
        connected_websockets.remove(websocket)