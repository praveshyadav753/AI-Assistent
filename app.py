from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import threading
import json
import asyncio
from typing import List
import time
from contextlib import asynccontextmanager
import traceback

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
        self.message = "Voice Assistant Ready"
        self.status = "idle"

    def to_dict(self):
        return {
            "is_awake": self.is_awake,
            "is_listening": self.is_listening,
            "is_speaking": self.is_speaking,
            "current_command": self.current_command,
            "current_response": self.current_response,
            "message": self.message,
            "status": self.status
        }

    def reset(self):
        """Reset to default state"""
        self.is_awake = False
        self.is_listening = False
        self.is_speaking = False
        self.current_command = ""
        self.current_response = ""
        self.status = "idle"

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
    """
    global voice_thread, main_loop
    
    try:
        # Startup
        main_loop = asyncio.get_running_loop()
        print("[INFO] FastAPI starting up...")
        print("[INFO] Starting voice assistant thread...")

        voice_thread = threading.Thread(
            target=voice_thread_wrapper,
            daemon=True,
            name="VoiceAssistant"
        )
        voice_thread.start()

        # Wait a bit and check if thread started successfully
        time.sleep(2)
        if voice_thread.is_alive():
            print(f"[SUCCESS] Voice assistant started - Thread ID: {voice_thread.ident}")
            assistant_state.message = "Voice assistant ready. Waiting for wake word..."
        else:
            print("[ERROR] Voice assistant thread failed to start!")
            assistant_state.message = "Voice assistant failed to start"
        
        yield  # This is where the application runs
        
    except Exception as e:
        print(f"[ERROR] Startup failed: {e}")
        traceback.print_exc()
        yield
    finally:
        # Shutdown
        print("[INFO] Shutting down voice assistant...")
        assistant_state.message = "Shutting down..."

def voice_thread_wrapper():
    """Wrapper for voice thread with error handling"""
    try:
        handle_voice_command(send_update_to_clients)
    except Exception as e:
        print(f"[ERROR] Voice thread crashed: {e}")
        traceback.print_exc()
        assistant_state.message = "Voice assistant encountered an error"

# Create FastAPI app with lifespan handler
app = FastAPI(
    title="Voice Assistant API",
    description="Voice Assistant with Wake Word Detection and Desktop Automation",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Broadcast Function ---
async def broadcast_message(payload: dict):
    """
    Broadcasts a full JSON payload to all connected WebSocket clients.
    """
    if not connected_websockets:
        return
        
    disconnected = []
    for ws in connected_websockets:
        try:
            await ws.send_json(payload)
        except Exception as e:
            print(f"[WARN] Failed to send to websocket: {e}")
            disconnected.append(ws)
    
    # Clean up disconnected websockets
    for ws in disconnected:
        if ws in connected_websockets:
            connected_websockets.remove(ws)
            print(f"[INFO] Removed disconnected websocket. Remaining: {len(connected_websockets)}")

# --- Update Function Called from Voice Thread ---
def send_update_to_clients(event_type: str, data: dict = None):
    """
    This function is called FROM the voice assistant thread.
    It safely schedules the async broadcast function to run on the main FastAPI event loop.
    """
    global main_loop, assistant_state
    
    if not data:
        data = {}

    try:
        # Update assistant state based on event type
        if event_type == "status_update":
            assistant_state.message = data.get("message", assistant_state.message)
            if "Waiting for wake word" in assistant_state.message:
                assistant_state.reset()
                assistant_state.status = "waiting"
            elif "error" in assistant_state.message.lower():
                assistant_state.status = "error"
                
        elif event_type == "wake_word_detected":
            assistant_state.is_awake = True
            assistant_state.status = "awake"
            assistant_state.message = "Wake word detected!"
            
        elif event_type == "direct_wakeup":
            assistant_state.is_awake = True
            assistant_state.status = "awake"
            assistant_state.message = "Direct wakeup activated"
            
        elif event_type == "listening_started":
            assistant_state.is_listening = True
            assistant_state.is_awake = True
            assistant_state.status = "listening"
            assistant_state.message = "Listening for your command..."
            assistant_state.current_command = ""
            assistant_state.current_response = ""
            
        elif event_type == "command_recognized":
            assistant_state.is_listening = False
            assistant_state.current_command = data.get("command", "")
            assistant_state.status = "processing"
            assistant_state.message = "Processing your command..."
            
        elif event_type == "response_generated":
            assistant_state.is_speaking = True
            assistant_state.is_awake = False
            assistant_state.status = "speaking"
            assistant_state.current_response = data.get("response", "")
            assistant_state.message = "Generating response..."
            
        elif event_type == "speaking_finished":
            assistant_state.is_speaking = False
            assistant_state.status = "idle"
            assistant_state.message = "Ready for next command"

        payload = {
            "type": event_type,
            "data": data,
            "assistant_state": assistant_state.to_dict(),
            "timestamp": time.time()
        }
        
        # Schedule the broadcast on the main loop
        if main_loop and main_loop.is_running():
            asyncio.run_coroutine_threadsafe(broadcast_message(payload), main_loop)
        else:
            print(f"[WARN] Main loop not available for event: {event_type}")
            
    except Exception as e:
        print(f"[ERROR] Failed to send update: {e}")
        traceback.print_exc()

# --- API Endpoints ---
@app.get("/")
async def root():
    return {
        "message": "Voice Assistant API is running",
        "status": "healthy",
        "assistant_state": assistant_state.to_dict()
    }

@app.get("/api/status")
async def get_status():
    """Get detailed status of the voice assistant"""
    global voice_thread
    
    thread_status = {
        "exists": voice_thread is not None,
        "alive": voice_thread.is_alive() if voice_thread else False,
        "name": voice_thread.name if voice_thread else None,
        "ident": voice_thread.ident if voice_thread else None
    }
    
    return {
        "voice_assistant_running": thread_status["alive"],
        "status": "running" if thread_status["alive"] else "stopped",
        "assistant_state": assistant_state.to_dict(),
        "thread_info": thread_status,
        "connected_clients": len(connected_websockets),
        "timestamp": time.time()
    }

@app.post("/api/wakeup")
async def trigger_wakeup():
    """Trigger direct wakeup of the voice assistant"""
    try:
        if not voice_thread or not voice_thread.is_alive():
            raise HTTPException(status_code=503, detail="Voice assistant is not running")
        
        direct_wakeup_flag.set()
        send_update_to_clients("direct_wakeup", {"message": "Direct wakeup triggered"})
        
        return {
            "status": "success", 
            "message": "Direct wakeup triggered",
            "timestamp": time.time()
        }
    except Exception as e:
        print(f"[ERROR] Wakeup trigger failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger wakeup: {str(e)}")

# Legacy endpoint for compatibility
@app.post("/start-wakeup/")
async def start_wakeup():
    """Legacy endpoint for backward compatibility"""
    return await trigger_wakeup()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client_id = f"{websocket.client.host}:{websocket.client.port}"
    print(f"[INFO] WebSocket connected: {client_id} - Total connections: {len(connected_websockets) + 1}")
    connected_websockets.append(websocket)
    
    try:
        # Send initial state to the newly connected client
        initial_payload = {
            "type": "initial_state",
            "message": "Connected to voice assistant",
            "assistant_state": assistant_state.to_dict(),
            "timestamp": time.time()
        }
        await websocket.send_json(initial_payload)
        
        # Keep the connection alive and handle incoming messages
        while True:
            try:
                # Wait for any message from the client (with timeout)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Handle client messages
                try:
                    client_msg = json.loads(data)
                    msg_type = client_msg.get("type", "unknown")
                    
                    if msg_type == "ping":
                        await websocket.send_json({
                            "type": "pong", 
                            "timestamp": time.time()
                        })
                    elif msg_type == "wakeup":
                        await trigger_wakeup()
                        
                except json.JSONDecodeError:
                    # Handle plain text messages
                    if data.strip().lower() == "ping":
                        await websocket.send_text("pong")
                        
            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_json({
                        "type": "keepalive",
                        "timestamp": time.time()
                    })
                except:
                    break  # Connection broken
                    
    except WebSocketDisconnect:
        print(f"[INFO] WebSocket disconnected: {client_id} - Remaining connections: {len(connected_websockets) - 1}")
    except Exception as e:
        print(f"[ERROR] WebSocket error for {client_id}: {e}")
    finally:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "voice_assistant": "running" if (voice_thread and voice_thread.is_alive()) else "stopped",
        "timestamp": time.time()
    }

# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    print(f"[ERROR] Unhandled exception: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "timestamp": time.time()
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)