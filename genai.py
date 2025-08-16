import google.generativeai as genai
import os
import json

# Your API key is hardcoded here. It's a security risk. 
# A safer way is to use environment variables like:
# genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
genai.configure(api_key="AIzaSyBjWQtVYLgt9-mkeunZsA74WsI2l1euKIs")

# The prompt is now passed directly to the GenerativeModel constructor
LLM_PROMPT = """You are a Desktop Automation Planner and Answerer and your name is nesty from india.

Your job:
1) If the user request is for an action on the computer, convert it into a step-by-step JSON action plan the automation system can execute.
2) If the request is a question (not an action), reply with a short, direct plain-text answer.

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
3) Use wait steps where UIs load.
4) Prefer wait_for_image/find_and_click_image over coordinates.

5) Use absolute paths and explicit URLs.
6) For delete_file, include "confirm": true when you truly intend deletion.
7) For open_app, search for it via the Win key if needed.
8) dont wrape answer in any kind of quote and md notation and appname should be ust app: appname 

Rules for answer responses:
- Output plain text only.
- Be concise and factual.
- Do NOT output JSON if the request is just a question.

Examples:
User: "Open Chrome and search cats"
Output:
[
  {"action": "open_browser", "params": {"url": "https://www.google.com"}},
  {"action": "wait", "params": {"seconds": 2}},
  {"action": "keyboard_type", "params": {"text": "cats"}},
  {"action": "keyboard_press", "params": {"key": "enter"}}
]
User: "Open whatsapp and type message"
Output:note its app not app_name
[
  {"action": "open_app", "params": {"app": "whatsapp"}},
  {"action": "wait", "params": {"seconds": 2}},
  {"action": "keyboard_type", "params": {"text": "username"}},
  {"action": "keyboard_press", "params": {"key": "enter"}}

User: "What time is it?"
Output:
It is 3:45 PM ist.

"""

# We now create the model instance with the system instruction
model = genai.GenerativeModel(model_name="gemini-2.5-flash", system_instruction=LLM_PROMPT)

def gemini_structured_response(user_text):
    # The prompt is already set in the model instance, so we just pass the user text
    response = model.generate_content(user_text)
    
    text_output = None
    if hasattr(response, "text") and response.text:  
        text_output = response.text.strip()
    elif hasattr(response, "candidates") and response.candidates:
        parts = response.candidates[0].content.parts
        if parts and hasattr(parts[0], "text"):
            text_output = parts[0].text.strip()

    if not text_output:
        raise ValueError("No valid text output returned from Gemini model")

    print(text_output)  # Debug: see raw output

    try:
        data = json.loads(text_output)
        return {"intent": "action", "data": data}
    except json.JSONDecodeError:
        return {"intent": "answer", "data": text_output}

# if __name__ == "__main__":
#     res1 = gemini_structured_response("Open Notepad")
#     print(res1)
#     res2 = gemini_structured_response("What's quantum computing?")
#     print(res2)