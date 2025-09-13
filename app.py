from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import threading
import json
import asyncio
from typing import List
import time
from contextlib import asynccontextmanager

from main import handle_voice_command, direct_wakeup_flag

# --- Assistant State Definition ---
class AssistantState:
    """A simple class to hold the assistant's state."""
    def __init__(self):
        self.is_awake = False
        self.is_listening = False
        self.is_speaking = False
        self.current_command = ""
        self.current_response = ""
        self.message = ""

    def to_dict(self):
        return self.__dict__

# Create the global state object and main event loop variable
assistant_state = AssistantState()
main_loop = None
voice_thread = None
connected_websockets: List[WebSocket] = []

# --- Lifespan Context Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager to handle startup and shutdown events.
    This replaces the deprecated @app.on_event decorators.
    """
    # Startup
    global voice_thread, main_loop
    
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
    
    yield  # This is where the application runs
    
    # Shutdown (cleanup code can go here if needed)
    print("[INFO] Shutting down voice assistant...")
    # Add any cleanup code here if necessary

# Create FastAPI app with lifespan handler
app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Broadcast Function ---
async def broadcast_message(payload: dict):
    """
    Broadcasts a full JSON payload to all connected WebSocket clients.
    """
    disconnected = []
    for ws in connected_websockets:
        try:
            await ws.send_json(payload)
        except Exception:
            # Mark broken connections for removal
            disconnected.append(ws)
    
    # Clean up disconnected websockets
    for ws in disconnected:
        if ws in connected_websockets:
            connected_websockets.remove(ws)

# --- Update Function Called from Voice Thread ---
def send_update_to_clients(event_type: str, data: dict = None):
    """
    This function is called FROM the voice assistant thread.
    It safely schedules the async broadcast function to run on the main FastAPI event loop.
    """
    global main_loop, assistant_state
    if not data:
        data = {}

    # Update assistant state based on event type
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
        asyncio.run_coroutine_threadsafe(broadcast_message(payload), main_loop)

# --- API Endpoints ---
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
    print(f"[INFO] WebSocket connected - Total connections: {len(connected_websockets) + 1}")
    connected_websockets.append(websocket)
    
    try:
        # Send initial state to the newly connected client
        initial_payload = {
            "type": "initial_state",
            "message": "Connected to voice assistant",
            "assistant_state": assistant_state.to_dict()
        }
        await websocket.send_json(initial_payload)
        
        # Keep the connection alive and handle incoming messages
        while True:
            # Wait for any message from the client (heartbeat/ping)
            data = await websocket.receive_text()
            # Optionally handle incoming messages from client here
            # For now, just keep the connection alive
            
    except WebSocketDisconnect:
        print(f"[INFO] WebSocket disconnected - Remaining connections: {len(connected_websockets) - 1}")
    except Exception as e:
        print(f"[ERROR] WebSocket error: {e}")
    finally:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)