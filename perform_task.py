import os
import subprocess
import platform
import pyautogui

def perform_task(command):
    system = platform.system().lower()

    command = command.lower()

    if "shutdown" in command:
        if system == "windows":
            os.system("shutdown /s /t 5")
        elif system == "linux" or system == "darwin":
            os.system("shutdown -h now")
        return "Shutting down..."

    elif "restart" in command:
        if system == "windows":
            os.system("shutdown /r /t 5")
        elif system == "linux" or system == "darwin":
            os.system("reboot")
        return "Restarting..."

    elif "close app" in command:
        # Example: Close notepad on Windows
        if system == "windows":
            os.system("taskkill /f /im notepad.exe")
        return "Closed app."

    elif "close current window" in command or "close tab" in command:
        # Works in most OS with keyboard shortcut
        pyautogui.hotkey('alt', 'f4')  # Windows/Linux
        # For macOS, you might use Command+W
        return "Closed current window/tab."

    elif "wifi" in command:
        if system == "windows":
            os.system("netsh interface set interface name=\"Wi-Fi\" admin=enabled")
        return "Wi-Fi toggled."

    elif "bluetooth" in command:
        if system == "windows":
            # This is tricky; you can toggle via PowerShell
            subprocess.run(["powershell", "-Command",
                            "Start-Process ms-settings:bluetooth"])
        return "Bluetooth toggled."

    elif "flight mode" in command:
        if system == "windows":
            # Opens the airplane mode settings
            subprocess.run(["powershell", "-Command",
                            "Start-Process ms-settings:network-airplanemode"])
        return "Opened flight mode settings."

    else:
        return "Command not recognized."
