"""Cross-platform abstraction layer (Gap 21).

Detects OS, provides platform-appropriate commands, paths, and behaviors.
Enables Sclerotium OS to run on Windows, Linux, and macOS.
"""

from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PlatformInfo:
    """Immutable platform information."""
    system: str           # "Windows" | "Linux" | "Darwin"
    release: str          # "11", "6.5", "24.1"
    machine: str          # "AMD64", "x86_64", "arm64"
    is_windows: bool = False
    is_linux: bool = False
    is_macos: bool = False
    home_dir: str = ""
    app_data_dir: str = ""


def detect_platform() -> PlatformInfo:
    """Detect current platform and return structured info."""
    sys_name = platform.system()
    is_win = sys_name == "Windows"
    is_lin = sys_name == "Linux"
    is_mac = sys_name == "Darwin"

    home = os.path.expanduser("~")
    if is_win:
        app_data = os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming"))
    elif is_mac:
        app_data = os.path.join(home, "Library", "Application Support")
    else:
        app_data = os.environ.get("XDG_DATA_HOME", os.path.join(home, ".local", "share"))

    return PlatformInfo(
        system=sys_name,
        release=platform.release(),
        machine=platform.machine(),
        is_windows=is_win,
        is_linux=is_lin,
        is_macos=is_mac,
        home_dir=home,
        app_data_dir=app_data,
    )


# Global singleton
_current = detect_platform()


def get_platform() -> PlatformInfo:
    return _current


def open_path(path: str) -> None:
    """Open a file/URL with the platform's default handler."""
    if _current.is_windows:
        os.startfile(path)  # type: ignore[attr-defined]
    elif _current.is_macos:
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def shell_command(cmd: str) -> str:
    """Platform-appropriate shell command wrapper."""
    if _current.is_windows:
        return cmd  # cmd.exe / PowerShell handles directly
    return cmd
