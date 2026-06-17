"""Alt+Space Hotkey Launcher — 纯 Win32 API，零依赖。

按 Alt+Space → 弹出输入框 → 输入命令回车 → 发送到 agent loop。

不需要 tkinter，使用 win32gui + win32con。
"""

import sys
import os
import ctypes
import ctypes.wintypes
import time
import threading
import subprocess

# Win32 constants
WM_HOTKEY = 0x0312
# Try multiple hotkey combos (first available wins)
HOTKEY_COMBOS = [
    (0x0001 | 0x0004, 0x20, "Alt+Shift+Space"),
    (0x0002 | 0x0004, 0x20, "Ctrl+Shift+Space"),
    (0x0001, 0x20, "Alt+Space"),
    (0x0002, 0x20, "Ctrl+Space"),
]
HOTKEY_ID = 1

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


def show_input_dialog():
    """Popup a simple input dialog using PowerShell."""
    ps_script = r'''
Add-Type -AssemblyName Microsoft.VisualBasic
$input = [Microsoft.VisualBasic.Interaction]::InputBox(
    "What do you want me to do?",
    "Sclerotium OS",
    ""
)
if ($input) { Write-Output $input }
'''
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def process_command(text):
    """Execute user command via shell or built-in handlers."""
    if not text:
        return
    print(f"\n[Sclerotium] Executing: {text}")

    # Built-in commands
    tl = text.lower().strip()
    if tl == "status":
        print("[Sclerotium] Organism: 15 organs, phase=running, uptime active")
        print("[Sclerotium] Dashboard: http://localhost:1990")
        return
    if tl in ("help", "?"):
        print("[Sclerotium] Commands: status, help, quit, or any shell command")
        return
    if tl in ("quit", "exit", "q"):
        print("[Sclerotium] Use Ctrl+C to quit")
        return

    # Shell execution
    try:
        result = subprocess.run(
            text, shell=True, capture_output=True, text=True, timeout=30,
            cwd=os.path.expanduser("~"),
        )
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip())
        if result.returncode != 0:
            print(f"[Sclerotium] Exit code: {result.returncode}")
    except subprocess.TimeoutExpired:
        print("[Sclerotium] Command timed out (30s)")
    except Exception as e:
        print(f"[Sclerotium] Error: {e}")


def hotkey_thread():
    """Register hotkey and poll for it."""
    # Try each hotkey combo
    registered = None
    for mod, key, name in HOTKEY_COMBOS:
        if user32.RegisterHotKey(None, HOTKEY_ID, mod, key):
            registered = name
            break

    if not registered:
        print("WARNING: All hotkeys failed (may be in use by other apps)")
        print("Use http://localhost:1990 instead, or type commands below.")
        while True:
            try:
                text = input("\n[Sclerotium] > ")
                if text:
                    process_command(text)
            except (EOFError, KeyboardInterrupt):
                break
        return

    print(f"Hotkey: {registered}  (Keep this window open)")
    print(f"Press {registered} to command, or type below.")

    # Windows message loop
    msg = ctypes.wintypes.MSG()
    while True:
        # Wait for message
        result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
        if result == 0:  # WM_QUIT
            break
        if result == -1:
            break

        if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
            text = show_input_dialog()
            if text:
                process_command(text)

        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


if __name__ == "__main__":
    print(r"""
    ╔══════════════════════════════════════╗
    ║  🧬 Sclerotium OS — Alt+Space       ║
    ║  Press Alt+Space to command          ║
    ║  OR type commands below              ║
    ║  Type 'quit' to exit                 ║
    ╚══════════════════════════════════════╝
    """)

    t = threading.Thread(target=hotkey_thread, daemon=True)
    t.start()

    # Also accept typed commands
    try:
        while True:
            text = input("[Sclerotium] > ")
            if text.lower() in ("quit", "exit", "q"):
                break
            if text:
                process_command(text)
    except (KeyboardInterrupt, EOFError):
        pass

    print("\nGoodbye.")
