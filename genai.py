# import google.generativeai as genai
# import os
# import json

# # Your API key is hardcoded here. It's a security risk. 
# # A safer way is to use environment variables like:
# # genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
# genai.configure(api_key="AIzaSyBjWQtVYLgt9-mkeunZsA74WsI2l1euKIs")

# # The prompt is now passed directly to the GenerativeModel constructor
# LLM_PROMPT = """You are a Desktop Automation Planner and Answerer and your name is nesty from india.

# Your job:
# 1) If the user request is for an action on the computer, convert it into a step-by-step JSON action plan the automation system can execute.
# 2) If the request is a question (not an action), reply with a short, direct plain-text answer.

# Use ONLY these actions (exact names):
# - open_app, open_browser, switch_window, close_app
# - keyboard_type, keyboard_press, keyboard_shortcut
# - mouse_click, mouse_move, mouse_drag
# - scroll
# - find_and_click_image, wait_for_image, read_text_from_screen
# - copy_file, move_file, delete_file, create_folder
# - run_command, take_screenshot
# - wait, if_condition

# Rules for action responses:
# 1) Output ONLY a valid JSON array for action requests. No extra text.
# 2) Each step is: {"action": "<name>", "params": {...}}
# 3) Use wait steps where UIs load.
# 4) Prefer wait_for_image/find_and_click_image over coordinates.

# 5) Use absolute paths and explicit URLs.
# 6) For delete_file, include "confirm": true when you truly intend deletion.
# 7) For open_app, search for it via the Win key if needed.
# 8) dont wrape answer in any kind of quote and md notation and appname should be ust app: appname 

# Rules for answer responses:
# - Output plain text only.
# - Be concise and factual.
# - Do NOT output JSON if the request is just a question.

# Examples:
# User: "Open Chrome and search cats"
# Output:
# [
#   {"action": "open_browser", "params": {"url": "https://www.google.com"}},
#   {"action": "wait", "params": {"seconds": 2}},
#   {"action": "keyboard_type", "params": {"text": "cats"}},
#   {"action": "keyboard_press", "params": {"key": "enter"}}
# ]
# User: "Open whatsapp and type message"
# Output:note its app not app_name
# [
#   {"action": "open_app", "params": {"app": "whatsapp"}},
#   {"action": "wait", "params": {"seconds": 2}},
#   {"action": "keyboard_type", "params": {"text": "username"}},
#   {"action": "keyboard_press", "params": {"key": "enter"}}

# User: "What time is it?"
# Output:
# It is 3:45 PM ist.

# """

# # We now create the model instance with the system instruction
# model = genai.GenerativeModel(model_name="gemini-2.5-flash", system_instruction=LLM_PROMPT)

# def gemini_structured_response(user_text):
#     # The prompt is already set in the model instance, so we just pass the user text
#     response = model.generate_content(user_text)
    
#     text_output = None
#     if hasattr(response, "text") and response.text:  
#         text_output = response.text.strip()
#     elif hasattr(response, "candidates") and response.candidates:
#         parts = response.candidates[0].content.parts
#         if parts and hasattr(parts[0], "text"):
#             text_output = parts[0].text.strip()

#     if not text_output:
#         raise ValueError("No valid text output returned from Gemini model")

#     print(text_output)  # Debug: see raw output

#     try:
#         data = json.loads(text_output)
#         return {"intent": "action", "data": data}
#     except json.JSONDecodeError:
#         return {"intent": "answer", "data": text_output}

# # if __name__ == "__main__":
# #     res1 = gemini_structured_response("Open Notepad")
# #     print(res1)
# #     res2 = gemini_structured_response("What's quantum computing?")
# #     print(res2)

import google.generativeai as genai
import os
import json
import traceback

# Configure API - Use environment variable for security
try:
    api_key = os.environ.get("GOOGLE_API_KEY", "AIzaSyBjWQtVYLgt9-mkeunZsA74WsI2l1euKIs")
    genai.configure(api_key=api_key)
    print("[INFO] Gemini API configured successfully")
except Exception as e:
    print(f"[ERROR] Failed to configure Gemini API: {e}")
    raise

LLM_PROMPT = """You are a Desktop Automation Planner and Answerer named Nesty .

Your job:
1) If the user request is for an action on the computer, convert it into a step-by-step JSON action plan.
2) If the request is a question (not an action), reply with a short, direct plain-text answer.
note : process the task and clear the intent if not clear instead of replying i cant do . 
Use ONLY these actions (exact names):
- open_app, open_browser, switch_window, close_app
- keyboard_type, keyboard_press, keyboard_shortcut
- mouse_click, mouse_move, mouse_drag
- scroll
- find_and_click_image, wait_for_image, read_text_from_screen
- copy_file, move_file, delete_file, create_folder
- run_command, take_screenshot
- wait, if_condition

Rules for action responses:
1) Output ONLY a valid JSON array for action requests. No extra text.
2) Each step is: {"action": "<name>", "params": {...}}
3) Use wait steps where UIs load (typically 3-4 seconds).
4) Prefer wait_for_image/find_and_click_image over coordinates.
5) Use absolute paths and explicit URLs.
6) For delete_file, include "confirm": true when you truly intend deletion.
7) For open_app, use simple app names: {"action": "open_app", "params": {"app": "notepad"}}
8) Don't wrap answer in quotes or markdown notation.
 for each step the next step will wait for 2 sec so that it dont miss the steps
i said to code the then code in default python by opening vs code   .
Rules for answer responses:
- Output plain text only.
- Be concise and factual.
- Do NOT output JSON if the request is just a question.
the position should be in list not diffrent .
 - if the user say to play something in youtube then after openning youtube wait 4 sec for search you have to press / key after that start type and play each step need wait 2 sec 
Examples:
User: "Open Chrome and search cats"
Output:
[
  {"action": "open_browser", "params": {"url": "https://www.google.com"}},
  {"action": "wait", "params": {"seconds": 2}},
  {"action": "keyboard_type", "params": {"text": "cats"}},
  {"action": "keyboard_press", "params": {"key": "enter"}}
]

User: "Open WhatsApp and type message"
Output:
[
  {"action": "open_app", "params": {"app": "whatsapp"}},
  {"action": "wait", "params": {"seconds": 3}},
  {"action": "keyboard_type", "params": {"text": "Hello from Nesty!"}}
]

User: "What time is it?"
Output:
It is 3:45 PM IST.

User: "Open notepad"
Output:
[
  {"action": "open_app", "params": {"app": "notepad"}},
  {"action": "wait", "params": {"seconds": 2}}
]
"""

# Create the model instance with the system instruction
try:
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        system_instruction=LLM_PROMPT,
        generation_config={
            "temperature": 0.1,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 2048,
        }
    )
    print("[INFO] Gemini model initialized successfully")
except Exception as e:
    print(f"[ERROR] Failed to initialize Gemini model: {e}")
    raise

def clean_json_output(text_output: str) -> str:
    """Clean common JSON formatting issues from model output"""
    # Remove markdown code blocks
    if "```json" in text_output:
        text_output = text_output.split("```json")[1].split("```")[0].strip()
    elif "```" in text_output:
        text_output = text_output.split("```")[1].split("```")[0].strip()
    
    # Remove any leading/trailing text that's not JSON
    text_output = text_output.strip()
    
    # Find the first '[' or '{' and last ']' or '}'
    start_idx = -1
    end_idx = -1
    
    for i, char in enumerate(text_output):
        if char in '[{' and start_idx == -1:
            start_idx = i
        if char in ']}':
            end_idx = i
    
    if start_idx != -1 and end_idx != -1:
        text_output = text_output[start_idx:end_idx+1]
    
    return text_output

def gemini_structured_response(user_text: str, max_retries: int = 2):
    """
    Get structured response from Gemini with better error handling
    """
    if not user_text or not user_text.strip():
        return {"intent": "answer", "data": "I didn't hear anything. Please try again."}
    
    print(f"[INFO] Sending to Gemini: '{user_text[:100]}{'...' if len(user_text) > 100 else ''}'")
    
    for attempt in range(max_retries + 1):
        try:
            # Generate content with timeout
            response = model.generate_content(
                user_text,
                request_options={"timeout": 30}
            )
            
            # Extract text from response
            text_output = None
            if hasattr(response, "text") and response.text:  
                text_output = response.text.strip()
            elif hasattr(response, "candidates") and response.candidates:
                parts = response.candidates[0].content.parts
                if parts and hasattr(parts[0], "text"):
                    text_output = parts[0].text.strip()

            if not text_output:
                print(f"[WARN] Empty response from Gemini on attempt {attempt + 1}")
                if attempt < max_retries:
                    continue
                return {"intent": "answer", "data": "I'm having trouble processing that request right now."}

            print(f"[DEBUG] Gemini raw output: {text_output[:200]}{'...' if len(text_output) > 200 else ''}")

            # Try to parse as JSON first
            try:
                # Clean the output
                cleaned_output = clean_json_output(text_output)
                data = json.loads(cleaned_output)
                
                # Validate that it's a list of actions
                if isinstance(data, list) and all(isinstance(item, dict) and "action" in item for item in data):
                    print(f"[INFO] Parsed {len(data)} automation steps")
                    return {"intent": "action", "data": data}
                else:
                    print("[WARN] Invalid action format, treating as answer")
                    return {"intent": "answer", "data": text_output}
                    
            except json.JSONDecodeError as je:
                # Not JSON, treat as answer
                print(f"[INFO] Response is not JSON (treating as answer): {str(je)[:100]}")
                return {"intent": "answer", "data": text_output}

        except Exception as e:
            print(f"[ERROR] Gemini API call failed on attempt {attempt + 1}: {e}")
            if "timeout" in str(e).lower():
                print("[WARN] Request timed out")
            elif "quota" in str(e).lower() or "limit" in str(e).lower():
                print("[ERROR] API quota exceeded")
                return {"intent": "answer", "data": "I'm temporarily unavailable due to high demand. Please try again in a moment."}
            elif attempt < max_retries:
                print(f"[INFO] Retrying... ({attempt + 1}/{max_retries})")
                continue
            else:
                traceback.print_exc()
                return {"intent": "answer", "data": "I'm having technical difficulties right now. Please try again later."}
    
    # All attempts failed
    return {"intent": "answer", "data": "I'm unable to process your request right now. Please try again."}

def test_gemini():
    """Test the Gemini integration"""
    test_cases = [
        "Open Notepad",
        "What's the weather like?", 
        "Open Chrome and search for Python tutorials",
        "Tell me a joke"
    ]
    
    for test in test_cases:
        print(f"\n--- Testing: {test} ---")
        try:
            result = gemini_structured_response(test)
            print(f"Intent: {result['intent']}")
            if result['intent'] == 'action':
                print(f"Actions: {len(result['data'])} steps")
                for i, action in enumerate(result['data']):
                    print(f"  {i+1}. {action.get('action', 'unknown')}: {action.get('params', {})}")
            else:
                print(f"Answer: {result['data'][:100]}{'...' if len(result['data']) > 100 else ''}")
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    test_gemini()