# controller.py
"""
A universal desktop automation controller that executes a series of steps
defined in a JSON format. It supports a wide range of actions from opening
applications and browsing URLs to controlling the mouse, keyboard, and filesystem.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

# --- Optional Dependencies (Guarded Imports) ---
try:
    import pyautogui  # type: ignore
    # Move mouse to a corner (0,0) to trigger a failsafe and abort
    pyautogui.FAILSAFE = True
except ImportError:
    pyautogui = None  # type: ignore

try:
    from PIL import Image  # type: ignore
except ImportError:
    Image = None  # type: ignore

try:
    import pytesseract  # type: ignore
except ImportError:
    pytesseract = None  # type: ignore

try:
    import psutil  # type: ignore
except ImportError:
    psutil = None  # type: ignore

try:
    import pygetwindow as gw  # type: ignore
except ImportError:
    gw = None  # type: ignore


# ---------------------------
# Config & Safety
# ---------------------------
@dataclass
class SafetyConfig:
    """Configuration for safety constraints on the executor."""
    allow_apps: Optional[List[str]] = None      # e.g., ["notepad", "code", "chrome"]
    allow_commands: Optional[List[str]] = None  # Allowlisted shell commands
    allow_urls: Optional[List[str]] = None      # URL prefixes or specific domains
    destructive_confirm: bool = True            # Require explicit confirm flag for destructive actions

DEFAULT_SAFETY = SafetyConfig(
    allow_apps=None,
    allow_commands=None,
    allow_urls=["http://", "https://", "file://"],
    destructive_confirm=True,
)


# ---------------------------
# Utilities
# ---------------------------

def _require(module: Any, name: str):
    """Raises a RuntimeError if a required module is not installed."""
    if module is None:
        raise RuntimeError(
            f"'{name}' is required for this action. Please install it, e.g., 'pip install {name}'"
        )

def _sleep(seconds: float):
    """Sleeps for a given duration, ensuring it's non-negative."""
    time.sleep(max(0.0, float(seconds)))

def _log(msg: str):
    """Prints a message with a timestamp."""
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def _platform_is_windows() -> bool:
    """Checks if the current operating system is Windows."""
    return platform.system().lower() == "windows"

def _normalize_path(p: Union[str, Path]) -> str:
    """Resolves and expands a path to its absolute form."""
    return str(Path(p).expanduser().resolve())

def _strip_quotes(s: str) -> str:
    """Strips leading/trailing single or double quotes from a string."""
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or \
       (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


# ---------------------------
# Condition Evaluation DSL for `if_condition`
# ---------------------------

class ConditionContext:
    """Provides functions that can be evaluated within a condition string."""
    def window_open(self, title_substr: str) -> bool:
        _require(gw, "pygetwindow")
        try:
            wins = gw.getAllTitles()
            return any(title_substr.lower() in t.lower() for t in wins if t.strip())
        except Exception:
            return False

    def image_visible(self, image_path: str, confidence: float = 0.8) -> bool:
        _require(pyautogui, "pyautogui")
        try:
            loc = pyautogui.locateOnScreen(_normalize_path(image_path), confidence=confidence)
            return loc is not None
        except Exception:
            return False

    def file_exists(self, path: str) -> bool:
        return Path(_normalize_path(path)).exists()

def evaluate_condition(expr: str, ctx: Optional[ConditionContext] = None) -> bool:
    """
    A safe, simple parser for condition strings. Avoids using `eval()`.
    Supports: function('arg'), not function('arg')
    """
    ctx = ctx or ConditionContext()
    s = expr.strip()

    is_negated = s.lower().startswith("not ")
    if is_negated:
        s = s[4:].strip()

    result = False
    supported_fns = {
        "window_open": ctx.window_open,
        "image_visible": ctx.image_visible,
        "file_exists": ctx.file_exists,
    }

    for name, fn in supported_fns.items():
        prefix = f"{name}("
        if s.startswith(prefix) and s.endswith(")"):
            arg_str = s[len(prefix) : -1]
            result = fn(_strip_quotes(arg_str))
            break
    
    return not result if is_negated else result


# ---------------------------
# Action Executor
# ---------------------------

class DesktopExecutor:
    def __init__(self, safety: SafetyConfig = DEFAULT_SAFETY):
        self.safety = safety

    # ---- App & Window ----
    def open_app(self, app: str):
        if self.safety.allow_apps and app.lower() not in self.safety.allow_apps:
            raise PermissionError(f"App not allowed by safety policy: {app}")
        _log(f"Opening app: {app}")

        if _platform_is_windows():
            try:
                # First, try direct execution for common, predictable app names
                common_apps = {
                    'notepad': 'notepad.exe',
                    'calculator': 'calc.exe',
                    'paint': 'mspaint.exe',
                    'cmd': 'cmd.exe',
                    'powershell': 'powershell.exe',
                    'explorer': 'explorer.exe'
                }
                app_lower = app.lower()
                if app_lower in common_apps:
                    subprocess.Popen(common_apps[app_lower])
                    return
                
                # If not a common app, use the Start menu search method
                _require(pyautogui, "pyautogui")
                pyautogui.hotkey("win")
                time.sleep(0.8)  # Wait for Start menu to open
                pyautogui.typewrite(app, interval=0.05)
                time.sleep(1.0)  # Wait for search results
                pyautogui.press("enter")
                
            except Exception as e:
                _log(f"Error opening app '{app}': {e}")
                raise RuntimeError(f"Failed to open application: {app}")
        else:
            # For macOS/Linux, a more general approach
            subprocess.Popen([app], shell=True)

    def open_browser(self, url: str):
        from webbrowser import open as wb_open
        if self.safety.allow_urls and not any(url.startswith(p) for p in self.safety.allow_urls):
            raise PermissionError(f"URL not allowed by safety policy: {url}")
        _log(f"Opening browser to: {url}")
        wb_open(url)

    def switch_window(self, window_title: str, exact: bool = False):
        _require(gw, "pygetwindow")
        _log(f"Switching to window containing: '{window_title}'")
        windows = gw.getAllWindows()
        target = None
        for w in windows:
            if not w.title.strip():
                continue
            if (exact and w.title == window_title) or \
               (not exact and window_title.lower() in w.title.lower()):
                target = w
                break
        if not target:
            raise RuntimeError(f"Window not found: {window_title}")
        target.activate()

    def close_app(self, window_title: str):
        _require(gw, "pygetwindow")
        _log(f"Closing app with window title: '{window_title}'")
        wins = gw.getWindowsWithTitle(window_title)
        if not wins:
            _log(f"Warning: No window with title '{window_title}' found to close.")
            return
        for w in wins:
            try:
                w.close()
            except Exception as e:
                _log(f"Could not close window '{w.title}': {e}")

    # ---- Keyboard ----
    def keyboard_type(self, text: str, interval: float = 0.02):
        _require(pyautogui, "pyautogui")
        _log(f"Typing text: '{text}'")
        pyautogui.typewrite(text, interval=interval)

    def keyboard_press(self, key: str):
        _require(pyautogui, "pyautogui")
        _log(f"Pressing key: {key}")
        pyautogui.press(key)

    def keyboard_shortcut(self, keys: List[str]):
        _require(pyautogui, "pyautogui")
        _log(f"Pressing shortcut: {' + '.join(keys)}")
        pyautogui.hotkey(*keys)

    # ---- Mouse ----
    def mouse_click(self, position: Optional[List[int]] = None, button: str = "left", clicks: int = 1, interval: float = 0.1):
        _require(pyautogui, "pyautogui")
        if position:
            x, y = position
            _log(f"Clicking {button} button {clicks}x at ({x},{y})")
            pyautogui.click(x, y, clicks=clicks, interval=interval, button=button)
        else:
            _log(f"Clicking {button} button {clicks}x at current position")
            pyautogui.click(clicks=clicks, interval=interval, button=button)

    def mouse_move(self, position: List[int], duration: float = 0.2):
        _require(pyautogui, "pyautogui")
        x, y = position
        _log(f"Moving mouse to ({x},{y}) over {duration}s")
        pyautogui.moveTo(x, y, duration=duration)

    def mouse_drag(self, from_pos: List[int], to_pos: List[int], duration: float = 0.3, button: str = "left"):
        _require(pyautogui, "pyautogui")
        x1, y1 = from_pos
        x2, y2 = to_pos
        _log(f"Dragging mouse from ({x1},{y1}) to ({x2},{y2})")
        pyautogui.moveTo(x1, y1)
        pyautogui.dragTo(x2, y2, duration=duration, button=button)

    # ---- Scroll ----
    def scroll(self, direction: str, distance: int):
        _require(pyautogui, "pyautogui")
        
        amount = distance
        if direction.lower() == "down":
            amount = -distance  # Make the value negative to scroll down
        elif direction.lower() != "up":
            # Handle cases where direction isn't 'up' or 'down'
            _log(f"Invalid scroll direction: '{direction}'. Defaulting to up.")

        _log(f"Scrolling by {amount} units ({direction} for a distance of {distance})")
        pyautogui.scroll(amount)

    # ---- Image/UI ----
    def find_and_click_image(self, image: str, confidence: float = 0.85, timeout: float = 10.0, click: bool = True):
        _require(pyautogui, "pyautogui")
        img_path = _normalize_path(image)
        _log(f"Finding image '{img_path}' with confidence > {confidence}")
        
        loc_center = None
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                box = pyautogui.locateOnScreen(img_path, confidence=confidence)
                if box:
                    loc_center = pyautogui.center(box)
                    break
            except Exception:
                pass # Image not found yet
            _sleep(0.25)
            
        if not loc_center:
            raise RuntimeError(f"Image not found on screen after {timeout}s: {img_path}")
        
        _log(f"Image found at: {loc_center}")
        if click:
            pyautogui.click(loc_center)
        return loc_center

    def wait_for_image(self, image: str, confidence: float = 0.85, timeout: float = 15.0):
        _require(pyautogui, "pyautogui")
        img_path = _normalize_path(image)
        _log(f"Waiting for image '{img_path}' to appear")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if pyautogui.locateOnScreen(img_path, confidence=confidence):
                    _log("Image found.")
                    return True
            except Exception:
                pass
            _sleep(0.25)
            
        _log(f"Image did not appear after {timeout}s.")
        return False

    def read_text_from_screen(self, region: Optional[List[int]] = None, lang: str = "eng") -> str:
        _require(pyautogui, "pyautogui")
        _require(Image, "Pillow")
        _require(pytesseract, "pytesseract")
        _log(f"Reading text from screen region: {region}")
        
        screenshot_args = {}
        if region:
            x, y, w, h = region
            screenshot_args['region'] = (x, y, w, h)
            
        img = pyautogui.screenshot(**screenshot_args)
        text = pytesseract.image_to_string(img, lang=lang).strip()
        _log(f"Read text: '{text[:100]}...'")
        return text

    # ---- Filesystem ----
    def copy_file(self, source: str, destination: str):
        src = _normalize_path(source)
        dst = _normalize_path(destination)
        _log(f"Copying file: {src} -> {dst}")
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    def move_file(self, source: str, destination: str):
        src = _normalize_path(source)
        dst = _normalize_path(destination)
        _log(f"Moving file: {src} -> {dst}")
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src, dst)

    def delete_file(self, path: str, confirm: bool = False):
        if self.safety.destructive_confirm and not confirm:
            raise PermissionError("delete_file requires `confirm=true` due to safety policy.")
        p = Path(_normalize_path(path))
        _log(f"Deleting path: {p}")
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()
        else:
            _log(f"Warning: Path not found for deletion: {p}")

    def create_folder(self, path: str):
        p = Path(_normalize_path(path))
        _log(f"Creating folder: {p}")
        p.mkdir(parents=True, exist_ok=True)

    # ---- System ----
    def run_command(self, command: str, cwd: Optional[str] = None) -> int:
        cmd_base = command.split()[0]
        if self.safety.allow_commands and cmd_base not in self.safety.allow_commands:
            raise PermissionError(f"Command not allowed by safety policy: {command}")
        _log(f"Running command: '{command}' in '{cwd or os.getcwd()}'")
        proc = subprocess.Popen(command, shell=True, cwd=cwd)
        return proc.wait()

    def take_screenshot(self, path: str, region: Optional[List[int]] = None):
        _require(pyautogui, "pyautogui")
        p = Path(_normalize_path(path))
        p.parent.mkdir(parents=True, exist_ok=True)
        _log(f"Taking screenshot -> {p}")

        screenshot_args = {}
        if region:
            x, y, w, h = region
            screenshot_args['region'] = (x, y, w, h)

        img = pyautogui.screenshot(**screenshot_args)
        img.save(str(p))

    # ---- Timing & Flow ----
    def wait(self, seconds: float):
        _log(f"Waiting for {seconds}s")
        _sleep(seconds)

    def if_condition(self, condition: str, then: List[dict], else_: Optional[List[dict]] = None):
        result = evaluate_condition(condition, ConditionContext())
        _log(f"Condition '{condition}' evaluated to: {result}")
        if result:
            self.execute_steps(then)
        elif else_:
            self.execute_steps(else_)

    # ---- Execution Engine ----
    def execute_steps(self, steps: List[Dict[str, Any]], dry_run: bool = False):
        """Executes a list of automation steps with validation and error handling."""
        for i, step in enumerate(steps):
            step_num = i + 1
            action = step.get("action")
            params = step.get("params", {}) or {}

            if not action:
                raise ValueError(f"Step {step_num} is missing an 'action'")

            if dry_run:
                _log(f"DRY-RUN {step_num:03d}: {action} {params}")
                continue

            handler = ACTION_HANDLERS.get(action)
            if not handler:
                raise ValueError(f"Unsupported action in step {step_num}: '{action}'")

            try:
                _log(f"EXECUTING {step_num:03d}: {action}")
                handler(self, **params)
                _log(f"COMPLETED {step_num:03d}: {action}")

            except TypeError as te:
                _log(f"ERROR in step {step_num}: Parameter mismatch for action '{action}'. Provided params: {list(params.keys())}. Details: {te}")
                raise
            except Exception as e:
                _log(f"ERROR in step {step_num}: Action '{action}' failed. Details: {e}")
                raise


# ---------------------------
# Action Registry
# ---------------------------
# Maps action name (string) to the corresponding DesktopExecutor method.
# This dictionary must be defined *after* the DesktopExecutor class.
ACTION_HANDLERS: Dict[str, Callable[..., Any]] = {
    "open_app": DesktopExecutor.open_app,
    "open_browser": DesktopExecutor.open_browser,
    "switch_window": DesktopExecutor.switch_window,
    "close_app": DesktopExecutor.close_app,
    "keyboard_type": DesktopExecutor.keyboard_type,
    "keyboard_press": DesktopExecutor.keyboard_press,
    "keyboard_shortcut": DesktopExecutor.keyboard_shortcut,
    "mouse_click": DesktopExecutor.mouse_click,
    "mouse_move": DesktopExecutor.mouse_move,
    "mouse_drag": DesktopExecutor.mouse_drag,
    "scroll": DesktopExecutor.scroll,
    "find_and_click_image": DesktopExecutor.find_and_click_image,
    "wait_for_image": DesktopExecutor.wait_for_image,
    "read_text_from_screen": DesktopExecutor.read_text_from_screen,
    "copy_file": DesktopExecutor.copy_file,
    "move_file": DesktopExecutor.move_file,
    "delete_file": DesktopExecutor.delete_file,
    "create_folder": DesktopExecutor.create_folder,
    "run_command": DesktopExecutor.run_command,
    "take_screenshot": DesktopExecutor.take_screenshot,
    "wait": DesktopExecutor.wait,
    "if_condition": DesktopExecutor.if_condition,
}


# ---------------------------
# CLI Runner
# ---------------------------

DEFAULT_PLAN_EXAMPLE = [
  {"action": "open_app", "params": {"app": "Notepad"}},
  {"action": "wait", "params": {"seconds": 2}},
  {"action": "keyboard_type", "params": {"text": "Hello, World!\nThis is an automated test."}},
  {"action": "wait", "params": {"seconds": 1}},
  {"action": "keyboard_shortcut", "params": {"keys": ["ctrl", "s"]}},
  {"action": "wait", "params": {"seconds": 1}},
  {"action": "keyboard_type", "params": {"text": "HelloWorld.txt"}},
  {"action": "keyboard_press", "params": {"key": "enter"}},
  {"action": "wait", "params": {"seconds": 2}},
  {"action": "close_app", "params": {"window_title": "HelloWorld.txt"}}
]

def main(argv: List[str]):
    """Main function to run the controller from the command line."""
    parser = argparse.ArgumentParser(description="Universal Desktop Controller")
    parser.add_argument(
        "plan",
        nargs="?",
        help="JSON string or path to a JSON file with steps. Uses a default example if not provided."
    )
    parser.add_argument("--dry", action="store_true", help="Dry-run (log actions without executing)")
    parser.add_argument("--safety", help="Path to a custom safety config JSON file")
    args = parser.parse_args(argv)

    safety = DEFAULT_SAFETY
    if args.safety:
        with open(args.safety, "r", encoding="utf-8") as f:
            s_config = json.load(f)
        safety = SafetyConfig(
            allow_apps=s_config.get("allow_apps"),
            allow_commands=s_config.get("allow_commands"),
            allow_urls=s_config.get("allow_urls"),
            destructive_confirm=bool(s_config.get("destructive_confirm", True)),
        )

    if args.plan:
        p = Path(args.plan)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                steps = json.load(f)
        else:
            try:
                steps = json.loads(args.plan)
            except json.JSONDecodeError:
                print(f"Error: Argument '{args.plan}' is not a valid file path or JSON string.")
                sys.exit(1)
    else:
        print("No plan provided. Running the default example plan.")
        steps = DEFAULT_PLAN_EXAMPLE

    print("--- Starting Automation Plan ---")
    try:
        executor = DesktopExecutor(safety=safety)
        executor.execute_steps(steps, dry_run=args.dry)
        print("--- Automation Plan Completed Successfully ---")
    except Exception as e:
        print(f"\n--- Automation Plan Failed ---")
        print(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    main(sys.argv[1:])