"""Perception — the organism's senses.

Monitors the host environment: windows, clipboard, filesystem, user activity.
All sensors publish events to the EventBus (nervous system).
"""

from perception.window_watcher import WindowWatcher
from perception.clipboard_watcher import ClipboardWatcher
from perception.file_watcher import FileWatcher
from perception.activity_tracker import ActivityTracker
from perception.user_model import UserModel, UserModelUpdater

__all__ = [
    "WindowWatcher",
    "ClipboardWatcher",
    "FileWatcher",
    "ActivityTracker",
    "UserModel",
    "UserModelUpdater",
]
