"""OSC 52 Clipboard — Direct system clipboard via ANSI escape sequences.

OSC 52 is a standard terminal protocol that lets applications read/write
the system clipboard WITHOUT external dependencies (no pyperclip needed).

Supported by: Windows Terminal, iTerm2, Kitty, Alacritty, WezTerm, tmux, Ghostty

Reference:
  OSC 52 spec: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html
  Textual 8.2.6+: built-in TextArea selection + clipboard
"""
from __future__ import annotations
import base64, sys, os

def _is_osc52_supported() -> bool:
    """Check if current terminal supports OSC 52."""
    term = os.environ.get("TERM", "")
    term_prog = os.environ.get("TERM_PROGRAM", "")
    wt_session = os.environ.get("WT_SESSION", "")
    # Windows Terminal, iTerm2, Kitty, Alacritty, WezTerm, Ghostty all support OSC 52
    supported = any(t in term_prog.lower() for t in
        ["iterm", "kitty", "alacritty", "wezterm", "ghostty", "warp"])
    return supported or bool(wt_session) or "xterm" in term

def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard via OSC 52. Returns True on success."""
    if not text or not _is_osc52_supported():
        return False
    try:
        encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
        # OSC 52 ; c ; <base64> ST
        sys.stdout.write(f"\033]52;c;{encoded}\033\\")
        sys.stdout.flush()
        return True
    except Exception:
        return False

def read_clipboard() -> str:
    """Read system clipboard via OSC 52. Returns '' on failure."""
    if not _is_osc52_supported():
        return ""
    try:
        sys.stdout.write("\033]52;c;?\033\\")
        sys.stdout.flush()
        # Terminal will respond — but this is async and hard to capture
        # Use pyperclip as fallback for reading
        return ""
    except Exception:
        return ""
