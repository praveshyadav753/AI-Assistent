import asyncio
from controller import DesktopExecutor, DEFAULT_SAFETY
from genai import gemini_structured_response
from speak import synthesize_text_to_speech
from perform_task import perform_task  # the offline command handler we defined

user_input = "open vs code"

async def handle_user_request(user_input):
    # Step 1: Check if the input can be handled offline
    offline_result = perform_task(user_input)
    
    if offline_result != "Command not recognized.":
        # If handled offline, provide feedback
        print(f"[Offline] {offline_result}")
        await synthesize_text_to_speech(offline_result)
        return

    # Step 2: Fallback to Gemini for structured response
    result = gemini_structured_response(user_input)

    if result["intent"] == "action":
        exec_ = DesktopExecutor(safety=DEFAULT_SAFETY)
        exec_.execute_steps(result["data"], dry_run=False)
        print("[Gemini] Action executed.")

    elif result["intent"] == "answer":
        await synthesize_text_to_speech(result["data"])
        print("[Gemini] Answer spoken.")


# Example usage
# if __name__ == "__main__":
#     asyncio.run(handle_user_request(user_input))
