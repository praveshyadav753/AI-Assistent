
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
from typing import Any, Dict, List, Optional, Tuple, Union, Callable

# Optional dependencies — guarded imports
try:
    import pyautogui  # type: ignore
    pyautogui.FAILSAFE = True  # move mouse to a corner to abort
except Exception as e:
    pyautogui = None  # type: ignore

try:
    from PIL import Image  # type: ignore
except Exception:
    Image = None  # type: ignore

try:
    import pytesseract  # type: ignore
except Exception:
    pytesseract = None  # type: ignore

try:
    import psutil  # type: ignore
except Exception:
    psutil = None  # type: ignore

try:
    import pygetwindow as gw  # type: ignore
except Exception:
    gw = None  # type: ignore


# ---------------------------
# Config & Safety
# ---------------------------
@dataclass
class SafetyConfig:
    allow_apps: Optional[List[str]] = None         # e.g., ["notepad.exe", "code", "chrome", "explorer.exe"]
    allow_commands: Optional[List[str]] = None     # allowlisted shell commands
    allow_urls: Optional[List[str]] = None         # prefixes e.g., ["https://", "http://", "file://"] or specific domains
    destructive_confirm: bool = True               # require explicit confirm flag for delete_file

DEFAULT_SAFETY = SafetyConfig(
    allow_apps=None,
    allow_commands=None,
    allow_urls=["http://", "https://", "file://"],
    destructive_confirm=True,
)


# ---------------------------
# Utilities
# ---------------------------

def _require(module, name: str):
    if module is None:
        raise RuntimeError(f"'{name}' is required for this action. Please install it.")


def _sleep(seconds: float):
    time.sleep(max(0.0, float(seconds)))


def _now_ms() -> int:
    return int(time.time() * 1000)


def _log(msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def _platform_is_windows() -> bool:
    return platform.system().lower() == "windows"


def _normalize_path(p: Union[str, Path]) -> str:
    return str(Path(p).expanduser().resolve())


# ---------------------------
# Condition DSL
# ---------------------------
# Supported conditions (strings):
#   window_open("TitleSubstr")
#   image_visible("path/to.png")
#   file_exists("path")
#   not <condition>
#
# Example param for if_condition:
# {"action":"if_condition","params":{"condition":"window_open('Chrome')","then":[...],"else":[...]}}

class ConditionContext:
    def window_open(self, title_substr: str) -> bool:
        if gw is None:
            return False
        try:
            wins = gw.getAllTitles()  # type: ignore
            return any(title_substr.lower() in t.lower() for t in wins if t.strip())
        except Exception:
            return False

    def image_visible(self, image_path: str, confidence: float = 0.8) -> bool:
        if pyautogui is None:
            return False
        image_path = _normalize_path(image_path)
        try:
            loc = pyautogui.locateOnScreen(image_path, confidence=confidence)  # type: ignore
            return loc is not None
        except Exception:
            return False

    def file_exists(self, path: str) -> bool:
        return Path(_normalize_path(path)).exists()


def evaluate_condition(expr: str, ctx: Optional[ConditionContext] = None) -> bool:
    """Very small parser for our mini DSL; no eval()."""
    ctx = ctx or ConditionContext()
    s = expr.strip()

    # Handle not <cond>
    if s.lower().startswith("not "):
        return not evaluate_condition(s[4:].strip(), ctx)

    def _extract_call(name: str) -> Optional[str]:
        prefix = f"{name}("
        if s.startswith(prefix) and s.endswith(")"):
            return s[len(prefix) : -1]
        return None

    arg = _extract_call("window_open")
    if arg is not None:
        return ctx.window_open(_strip_quotes(arg))

    arg = _extract_call("image_visible")
    if arg is not None:
        return ctx.image_visible(_strip_quotes(arg))

    arg = _extract_call("file_exists")
    if arg is not None:
        return ctx.file_exists(_strip_quotes(arg))

    # Unknown condition — default False
    return False


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


# ---------------------------
# Action Executor
# ---------------------------
class DesktopExecutor:
    def __init__(self, safety: SafetyConfig = DEFAULT_SAFETY):
        self.safety = safety

    # ---- App & Window ----
    def open_app(self, app: str):
        if self.safety.allow_apps and app not in self.safety.allow_apps:
            raise PermissionError(f"App not allowed by safety policy: {app}")
        _log(f"open_app: {app}")

        if _platform_is_windows():
            pyautogui.hotkey("win")
            time.sleep(0.5)
            pyautogui.typewrite(app)
            time.sleep(0.5)
            pyautogui.press("enter")


    def open_browser(self, url: str):
        from webbrowser import open as wb_open
        if self.safety.allow_urls and not any(url.startswith(p) for p in self.safety.allow_urls):
            raise PermissionError(f"URL not allowed by safety policy: {url}")
        _log(f"open_browser: {url}")
        wb_open(url)

    def switch_window(self, window_title: str, exact: bool = False):
        _require(gw, "pygetwindow")
        _log(f"switch_window: {window_title}")
        windows = gw.getAllTitles()  # type: ignore
        target = None
        for title in windows:
            if not title.strip():
                continue
            if (exact and title == window_title) or ((not exact) and window_title.lower() in title.lower()):
                target = title
                break
        if not target:
            raise RuntimeError(f"Window not found: {window_title}")
        w = gw.getWindowsWithTitle(target)[0]  # type: ignore
        w.activate()

    def close_app(self, app: Optional[str] = None, window_title: Optional[str] = None):
        _log(f"close_app: app={app} window_title={window_title}")
        if window_title and gw is not None:
            wins = gw.getWindowsWithTitle(window_title)  # type: ignore
            for w in wins:
                try:
                    w.close()
                except Exception:
                    pass
        if app and psutil is not None:
            for proc in psutil.process_iter(attrs=["name"]):
                try:
                    if proc.info["name"] and app.lower() in proc.info["name"].lower():
                        proc.terminate()
                except Exception:
                    pass

    # ---- Keyboard ----
    def keyboard_type(self, text: str, interval: float = 0.02):
        _require(pyautogui, "pyautogui")
        _log(f"keyboard_type: '{text}'")
        pyautogui.typewrite(text, interval=interval)  # type: ignore

    def keyboard_press(self, key: str):
        _require(pyautogui, "pyautogui")
        _log(f"keyboard_press: {key}")
        pyautogui.press(key)  # type: ignore

    def keyboard_shortcut(self, keys: List[str]):
        _require(pyautogui, "pyautogui")
        _log(f"keyboard_shortcut: {' + '.join(keys)}")
        pyautogui.hotkey(*keys)  # type: ignore

    # ---- Mouse ----
    def mouse_click(self, position: Optional[List[int]] = None, button: str = "left", clicks: int = 1, interval: float = 0.1):
        _require(pyautogui, "pyautogui")
        if position:
            x, y = position
            _log(f"mouse_click @ ({x},{y}) [{button}] x{clicks}")
            pyautogui.click(x, y, clicks=clicks, interval=interval, button=button)  # type: ignore
        else:
            _log(f"mouse_click at current [{button}] x{clicks}")
            pyautogui.click(clicks=clicks, interval=interval, button=button)  # type: ignore

    def mouse_move(self, position: List[int], duration: float = 0.2):
        _require(pyautogui, "pyautogui")
        x, y = position
        _log(f"mouse_move -> ({x},{y}) in {duration}s")
        pyautogui.moveTo(x, y, duration=duration)  # type: ignore

    def mouse_drag(self, from_pos: List[int], to_pos: List[int], duration: float = 0.3, button: str = "left"):
        _require(pyautogui, "pyautogui")
        x1, y1 = from_pos
        x2, y2 = to_pos
        _log(f"mouse_drag ({x1},{y1}) -> ({x2},{y2}) [{button}] in {duration}s")
        pyautogui.moveTo(x1, y1)  # type: ignore
        pyautogui.dragTo(x2, y2, duration=duration, button=button)  # type: ignore

    # ---- Scroll ----
    def scroll(self, amount: int):
        _require(pyautogui, "pyautogui")
        _log(f"scroll: {amount}")
        pyautogui.scroll(amount)  # type: ignore

    # ---- Image/UI ----
    def find_and_click_image(self, image: str, confidence: float = 0.85, timeout: float = 10.0, click: bool = True):
        _require(pyautogui, "pyautogui")
        img_path = _normalize_path(image)
        _log(f"find_and_click_image: {img_path} (conf={confidence}, timeout={timeout})")
        end = time.time() + timeout
        loc_center = None
        while time.time() < end:
            try:
                box = pyautogui.locateOnScreen(img_path, confidence=confidence)  # type: ignore
            except Exception:
                box = None
            if box:
                loc_center = pyautogui.center(box)  # type: ignore
                break
            _sleep(0.25)
        if not loc_center:
            raise RuntimeError(f"Image not found on screen: {img_path}")
        if click:
            pyautogui.click(loc_center)  # type: ignore
        return loc_center

    def wait_for_image(self, image: str, confidence: float = 0.85, timeout: float = 15.0):
        _require(pyautogui, "pyautogui")
        img_path = _normalize_path(image)
        _log(f"wait_for_image: {img_path} (conf={confidence}, timeout={timeout})")
        end = time.time() + timeout
        while time.time() < end:
            try:
                if pyautogui.locateOnScreen(img_path, confidence=confidence):  # type: ignore
                    return True
            except Exception:
                pass
            _sleep(0.25)
        return False

    def read_text_from_screen(self, region: Optional[List[int]] = None, lang: str = "eng") -> str:
        _require(pyautogui, "pyautogui")
        _require(Image, "Pillow")
        _require(pytesseract, "pytesseract")
        _log(f"read_text_from_screen: region={region}")
        if region:
            x, y, w, h = region
            img = pyautogui.screenshot(region=(x, y, w, h))  # type: ignore
        else:
            img = pyautogui.screenshot()  # type: ignore
        return pytesseract.image_to_string(img, lang=lang)  # type: ignore

    # ---- Filesystem ----
    def copy_file(self, source: str, target: str):
        src = _normalize_path(source)
        dst = _normalize_path(target)
        _log(f"copy_file: {src} -> {dst}")
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    def move_file(self, source: str, target: str):
        src = _normalize_path(source)
        dst = _normalize_path(target)
        _log(f"move_file: {src} -> {dst}")
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src, dst)

    def delete_file(self, path: str, confirm: bool = False):
        if self.safety.destructive_confirm and not confirm:
            raise PermissionError("delete_file requires confirm=true per safety policy")
        p = Path(_normalize_path(path))
        _log(f"delete_file: {p}")
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()

    def create_folder(self, path: str):
        p = Path(_normalize_path(path))
        _log(f"create_folder: {p}")
        p.mkdir(parents=True, exist_ok=True)

    # ---- System ----
    def run_command(self, command: str, cwd: Optional[str] = None) -> int:
        if self.safety.allow_commands and command.split()[0] not in self.safety.allow_commands:
            raise PermissionError(f"Command not allowed by safety policy: {command}")
        _log(f"run_command: {command}")
        proc = subprocess.Popen(command, shell=True, cwd=cwd)
        return proc.wait()

    def take_screenshot(self, path: str, region: Optional[List[int]] = None):
        _require(pyautogui, "pyautogui")
        p = Path(_normalize_path(path))
        p.parent.mkdir(parents=True, exist_ok=True)
        _log(f"take_screenshot -> {p} (region={region})")
        if region:
            x, y, w, h = region
            img = pyautogui.screenshot(region=(x, y, w, h))  # type: ignore
        else:
            img = pyautogui.screenshot()  # type: ignore
        img.save(str(p))

    # ---- Timing & Flow ----
    def wait(self, seconds: float):
        _log(f"wait: {seconds}s")
        _sleep(seconds)

    def if_condition(self, condition: str, then: List[dict], else_: Optional[List[dict]] = None, **kwargs):
        result = evaluate_condition(condition)
        _log(f"if_condition: '{condition}' => {result}")
        if result:
            self.execute_steps(then)
        elif else_:
            self.execute_steps(else_)

    # ---- Execution Engine ----
    def execute_steps(self, steps: List[Dict[str, Any]], dry_run: bool = False):
        for i, step in enumerate(steps):
            action = step.get("action")
            params = step.get("params", {}) or {}
            if not action:
                raise ValueError(f"Step {i} missing 'action'")
            if dry_run:
                _log(f"DRY-RUN {i+1:03d}: {action} {params}")
                continue
            handler = ACTION_HANDLERS.get(action)
            if not handler:
                raise ValueError(f"Unsupported action: {action}")
            # Map params to handler signature safely
            try:
                handler(self, **params)
            except TypeError as te:
                # Fallback: try passing the full params dict if signature mismatch
                handler(self, **{k: v for k, v in params.items()})


# Action registry maps action name -> DesktopExecutor method
ACTION_HANDLERS: Dict[str, Callable[..., Any]] = {
    # App & Window
    "open_app": DesktopExecutor.open_app,
    "open_browser": DesktopExecutor.open_browser,
    "switch_window": DesktopExecutor.switch_window,
    "close_app": DesktopExecutor.close_app,

    # Keyboard
    "keyboard_type": DesktopExecutor.keyboard_type,
    "keyboard_press": DesktopExecutor.keyboard_press,
    "keyboard_shortcut": DesktopExecutor.keyboard_shortcut,

    # Mouse
    "mouse_click": DesktopExecutor.mouse_click,
    "mouse_move": DesktopExecutor.mouse_move,
    "mouse_drag": DesktopExecutor.mouse_drag,

    # Scroll
    "scroll": DesktopExecutor.scroll,

    # Image/UI
    "find_and_click_image": DesktopExecutor.find_and_click_image,
    "wait_for_image": DesktopExecutor.wait_for_image,
    "read_text_from_screen": DesktopExecutor.read_text_from_screen,

    # Filesystem
    "copy_file": DesktopExecutor.copy_file,
    "move_file": DesktopExecutor.move_file,
    "delete_file": DesktopExecutor.delete_file,
    "create_folder": DesktopExecutor.create_folder,

    # System
    "run_command": DesktopExecutor.run_command,
    "take_screenshot": DesktopExecutor.take_screenshot,

    # Timing & Flow
    "wait": DesktopExecutor.wait,
    "if_condition": DesktopExecutor.if_condition,
}


# ---------------------------
# LLM Prompt Template
# ---------------------------
LLM_PROMPT = r"""
You are a Desktop Automation Planner.
Convert the user request into a step-by-step JSON action plan that the automation system can execute.
Use ONLY the following actions (and their exact names):
- open_app, open_browser, switch_window, close_app
- keyboard_type, keyboard_press, keyboard_shortcut
- mouse_click, mouse_move, mouse_drag
- scroll
- find_and_click_image, wait_for_image, read_text_from_screen
- copy_file, move_file, delete_file, create_folder
- run_command, take_screenshot
- wait, if_condition

Rules:
1) Output ONLY valid JSON array, no comments or extra text.
2) Each step is: {"action": "<name>", "params": { ... }}
3) Add wait steps where UIs load.
4) Prefer robust interactions (wait_for_image/find_and_click_image) over raw coordinates.
5) Use absolute paths and explicit URLs.
6) For delete_file, include "confirm": true when you truly intend deletion.
7) for opening application make sure to search application by pressing win key

Examples:
User: "Open Chrome and search cats"
Output:
[
  {"action": "open_browser", "params": {"url": "https://www.google.com"}},
  {"action": "wait", "params": {"seconds": 2}},
  {"action": "keyboard_type", "params": {"text": "cats"}},
  {"action": "keyboard_press", "params": {"key": "enter"}}
]

User: "Make a Reports folder on Desktop and take a screenshot"
Output:
[
  {"action": "create_folder", "params": {"path": "~/Desktop/Reports"}},
  {"action": "take_screenshot", "params": {"path": "~/Desktop/Reports/screen.png"}}
]
"""


# ---------------------------
# CLI helper
# ---------------------------
# DEFAULT_PLAN_EXAMPLE = # [
# #     {"action": "open_browser", "params": {"url": "https://www.youtube.com"}},
# #     {"action": "wait", "params": {"seconds": 5}},
# #     {"action": "keyboard_type", "params": {"text": "Tum Bin song"}},
# #     {"action": "keyboard_press", "params": {"key": "enter"}},
# # ]

# [
#   {"action": "open_app", "params": {"path": "C:/Users/YourUsername/AppData/Local/Programs/Microsoft VS Code/Code.exe"}},
#   {"action": "wait", "params": {"seconds": 3}},
#   {"action": "keyboard_shortcut", "params": {"keys": ["ctrl", "n"]}},
#   {"action": "wait", "params": {"seconds": 1}},
#   {"action": "keyboard_type", "params": {"text": "def fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        print(a)\n        a, b = b, a + b\n\nfibonacci(10)"}},
#   {"action": "wait", "params": {"seconds": 1}},
#   {"action": "keyboard_shortcut", "params": {"keys": ["ctrl", "s"]}},
#   {"action": "wait", "params": {"seconds": 1}},
#   {"action": "keyboard_type", "params": {"text": "fab_series.py"}},
#   {"action": "keyboard_press", "params": {"key": "enter"}}
# ]


def main(argv: List[str]):
    import argparse

    parser = argparse.ArgumentParser(description="Universal Desktop Controller")
    parser.add_argument("plan", nargs="?", help="JSON string or path to JSON file with steps")
    parser.add_argument("--dry", action="store_true", help="Dry-run (do not execute actions)")
    parser.add_argument("--safety", help="Path to safety config JSON (allowlists)")
    args = parser.parse_args(argv)

    safety = DEFAULT_SAFETY
    if args.safety:
        with open(args.safety, "r", encoding="utf-8") as f:
            s = json.load(f)
        safety = SafetyConfig(
            allow_apps=s.get("allow_apps"),
            allow_commands=s.get("allow_commands"),
            allow_urls=s.get("allow_urls"),
            destructive_confirm=bool(s.get("destructive_confirm", True)),
        )

    if args.plan is None:
        steps = DEFAULT_PLAN_EXAMPLE
    else:
        # If file exists, read from file; else treat as JSON string
        p = Path(args.plan)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                steps = json.load(f)
        else:
            steps = json.loads(args.plan)

    exec_ = DesktopExecutor(safety=safety)
    exec_.execute_steps(steps, dry_run=args.dry)


# if __name__ == "__main__":
#     main(sys.argv[1:])
