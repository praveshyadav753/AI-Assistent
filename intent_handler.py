import asyncio
import traceback
from controller import DesktopExecutor, DEFAULT_SAFETY
from genai import gemini_structured_response
from typing import Callable
from speak import synthesize_text_to_speech, speak_response
from perform_task import perform_task

async def handle_user_request(user_input,update_callback:callable=None):
    """
    Handle user requests with proper error handling and fallback logic.
    """
    if not user_input or not user_input.strip():
        await speak_response("I didn't hear anything. Please try again.")
        return

    print(f"[INFO] Processing request: '{user_input}'")
    
    try:
        # Step 1: Check if the input can be handled offline
        offline_result = perform_task(user_input)
        
        if offline_result != "Command not recognized.":
            # If handled offline, provide feedback
            print(f"[Offline] {offline_result}")
            await speak_response(offline_result)
            return

        # Step 2: Fallback to Gemini for structured response
        print("[INFO] Using Gemini AI for processing...")
        result = gemini_structured_response(user_input)

        if result["intent"] == "action":
            print(f"[INFO] Executing {len(result['data'])} automation steps")
            
            try:
                exec_ = DesktopExecutor(safety=DEFAULT_SAFETY)
                exec_.execute_steps(result["data"], dry_run=False)
                print("[Gemini] Action executed successfully.")
                await speak_response("Task completed successfully.")
                
            except Exception as exec_error:
                print(f"[ERROR] Action execution failed: {exec_error}")
                traceback.print_exc()
                await speak_response("Sorry, I encountered an error while performing that action.")

        elif result["intent"] == "answer":
            print(f"[INFO] Providing answer: {result['data'][:100]}...")
            await speak_response(result["data"])
            update_callback("response_generated", {"command": f"{result['data'][:]}"})     
            print("[Gemini] Answer spoken.")
            
        else:
            print(f"[WARN] Unknown intent: {result.get('intent', 'None')}")
            await speak_response("I'm not sure how to handle that request.")

    except Exception as e:
        print(f"[ERROR] Request handling failed: {e}")
        traceback.print_exc()
        
        # Provide user-friendly error message
        if "api" in str(e).lower() or "network" in str(e).lower():
            await speak_response("I'm having trouble connecting to my AI services. Please check your internet connection.")
        elif "timeout" in str(e).lower():
            await speak_response("The request took too long to process. Please try again.")
        else:
            await speak_response("I encountered an unexpected error. Please try rephrasing your request.")

# Wrapper function for compatibility
def handle_user_request_sync(user_input):
    """Synchronous wrapper for handle_user_request"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(handle_user_request(user_input))
    except Exception as e:
        print(f"[ERROR] Sync wrapper failed: {e}")
    finally:
        try:
            loop.close()
        except:
            pass