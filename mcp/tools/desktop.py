"""MCP Desktop Tools — 6 automation tools (octopus arm motor control).

Wired to real implementations:
  - ScreenAgent (screenshot + OCR)
  - UIAController (UIA element find/click/read)
  - InputSimulator (keyboard/mouse low-level)
  - VisionDesktopAgent (triple-channel chain execution)
  - AppLauncher (app/file open)
"""

from __future__ import annotations

import base64
import io
import logging
from typing import Any

from mcp.server import ToolRegistry

logger = logging.getLogger("sclerotium.mcp.desktop")

# ── Lazy-loaded singletons (heavy imports, init once) ────────────────────

_screen_agent = None
_uia_controller = None
_input_simulator = None
_vision_agent = None


def _get_screen_agent():
    global _screen_agent
    if _screen_agent is None:
        from automation.screen_agent import ScreenAgent
        _screen_agent = ScreenAgent()
    return _screen_agent


def _get_uia_controller():
    global _uia_controller
    if _uia_controller is None:
        from automation.uia_controller import UIAController
        _uia_controller = UIAController()
    return _uia_controller


def _get_input_simulator():
    global _input_simulator
    if _input_simulator is None:
        from automation.input_simulator import InputSimulator
        _input_simulator = InputSimulator()
    return _input_simulator


def _get_vision_agent():
    global _vision_agent
    if _vision_agent is None:
        from kernel.advanced.vision_desktop import VisionDesktopAgent
        _vision_agent = VisionDesktopAgent()
    return _vision_agent


# ── Tool handlers ────────────────────────────────────────────────────────


async def _desktop_screenshot(
    region: list[int] | None = None,
    ocr: bool = True,
    save_path: str = "",
) -> dict[str, Any]:
    """Capture screenshot with optional OCR analysis.

    Wired to: ScreenAgent.capture() + ScreenAgent.ocr_from_capture()
    """
    try:
        agent = _get_screen_agent()
        if not agent.available:
            return {"ok": False, "error": "Pillow not available for screenshot"}

        bbox: tuple[int, int, int, int] | None = None
        if region and len(region) == 4:
            bbox = (region[0], region[1], region[2], region[3])

        capture = agent.capture(region=bbox)
        if capture is None:
            return {"ok": False, "error": "Screenshot capture returned None"}

        result: dict[str, Any] = {
            "ok": True,
            "image_base64": capture.image_base64,
            "resolution": [capture.width, capture.height],
            "format": capture.format,
        }

        # BUG#1 + BUG#5 修复: OCR 可用性检测 + 清晰诊断信息
        result["ocr_available"] = agent.ocr_available
        result["ocr_backend"] = agent.ocr_backend_name

        if ocr and agent.ocr_available:
            ocr_result = agent.ocr_from_capture(capture)
            result["ocr_text"] = ocr_result.text
            result["ocr_confidence"] = ocr_result.confidence
            result["ocr_language"] = ocr_result.language
            result["ocr_regions"] = len(ocr_result.regions)
        elif ocr and not agent.ocr_available:
            result["ocr_text"] = ""
            result["ocr_available"] = False
            result["ocr_error"] = "OCR engine not available"
            result["ocr_fix"] = "Install: pip install pytesseract + download Tesseract-OCR from https://github.com/UB-Mannheim/tesseract/wiki (Windows)"
            result["ocr_note"] = "pytesseract not installed. Tesseract-OCR binary also required on Windows."

        # Save to disk if requested
        if save_path:
            try:
                img_bytes = base64.b64decode(capture.image_base64)
                with open(save_path, "wb") as f:
                    f.write(img_bytes)
                result["saved_to"] = save_path
            except Exception as e:
                result["save_error"] = str(e)

        return result

    except Exception as e:
        logger.error("desktop_screenshot failed: %s", e)
        return {"ok": False, "error": str(e)}


async def _desktop_click(
    target: str,
    method: str = "uia",
    x: int = 0,
    y: int = 0,
) -> dict[str, Any]:
    """Click UI element by name (UIA), OCR text, or raw coordinates.

    Wired to: UIAController.find_element() + UIAController.click()
              or InputSimulator.click() for coordinate-based clicks
    """
    try:
        # Strategy 1: UIA element search (method=uia or auto)
        if method in ("uia", "auto") and target:
            ctrl = _get_uia_controller()
            if ctrl.available:
                element = ctrl.find_element(name=target)
                if element is None:
                    element = ctrl.find_element(automation_id=target)
                if element is None:
                    element = ctrl.find_element(control_type=target)
                if element is not None:
                    result = ctrl.click(element=element)
                    return {
                        "ok": result.success,
                        "method": "uia",
                        "target": target,
                        "element_found": True,
                        "coordinates": list(element.center),
                        "detail": result.detail,
                    }

        # Strategy 2: OCR text search (method=ocr or auto fallback)
        if method in ("ocr", "auto") and target:
            screen = _get_screen_agent()
            if screen.available:
                pos = screen.find_text_on_screen(target)
                if pos is not None:
                    sim = _get_input_simulator()
                    result = sim.click(pos[0], pos[1])
                    return {
                        "ok": result.success,
                        "method": "ocr",
                        "target": target,
                        "element_found": True,
                        "coordinates": [pos[0], pos[1]],
                        "detail": f"OCR click at ({pos[0]}, {pos[1]})",
                    }

        # Strategy 3: Raw coordinate click
        if x > 0 or y > 0:
            sim = _get_input_simulator()
            result = sim.click(x, y)
            return {
                "ok": result.success,
                "method": "coordinate",
                "target": f"({x}, {y})",
                "element_found": True,
                "coordinates": [x, y],
                "detail": result.detail,
            }

        # Not found
        return {
            "ok": False,
            "method": method,
            "target": target,
            "element_found": False,
            "coordinates": [x, y],
            "detail": f"Element '{target}' not found via {method}",
        }

    except Exception as e:
        logger.error("desktop_click failed: %s", e)
        return {"ok": False, "error": str(e), "element_found": False}


async def _desktop_type(
    text: str,
    target: str = "",
) -> dict[str, Any]:
    """Type text into the focused element. Optionally click target first.

    Wired to: InputSimulator.type_text() (primary) or UIAController.type_text() (fallback)
    """
    if not text:
        return {"ok": False, "error": "No text provided"}

    try:
        # Click target element first if specified
        if target:
            click_result = await _desktop_click(target=target, method="auto")
            if not click_result.get("element_found"):
                return {
                    "ok": False,
                    "characters_typed": 0,
                    "detail": f"Could not find target '{target}' to focus before typing",
                }

        # Type via InputSimulator (most reliable)
        sim = _get_input_simulator()
        if sim.available:
            result = sim.type_text(text)
            return {
                "ok": result.success,
                "characters_typed": len(text) if result.success else 0,
                "detail": result.detail,
                "backend": sim.backend,
            }

        # Fallback to UIAController
        ctrl = _get_uia_controller()
        result = ctrl.type_text(text)
        return {
            "ok": result.success,
            "characters_typed": len(text) if result.success else 0,
            "detail": result.detail,
            "backend": "uia",
        }

    except Exception as e:
        logger.error("desktop_type failed: %s", e)
        return {"ok": False, "characters_typed": 0, "error": str(e)}


async def _desktop_open(
    target: str,
    args: list[str] | None = None,
) -> dict[str, Any]:
    """Open an application or file by name or path.

    Wired to: automation.app_launcher.AppLauncher.open()
    """
    try:
        from automation.app_launcher import AppLauncher
        launcher = AppLauncher()
        result = launcher.open(target, args)
        # AppLauncher.open returns a dict, ensure ok field
        if isinstance(result, dict):
            result.setdefault("ok", result.get("status") == "launched"
                                        or result.get("status") == "opened")
            return result
        return {"ok": True, "status": "launched", "detail": str(result)}
    except Exception as e:
        logger.error("desktop_open failed: %s", e)
        return {"ok": False, "error": str(e)}


async def _desktop_read(
    target: str = "",
    method: str = "uia",
) -> dict[str, Any]:
    """Read window/UI content — title, text, element tree.

    Wired to: UIAController.get_active_window() + UIAController.read_text()
    """
    try:
        ctrl = _get_uia_controller()

        # Get active window info
        window_info = ctrl.get_active_window()
        window_title = window_info.title if window_info else ""
        process_name = window_info.process_name if window_info else ""

        # If target specified, find that element; otherwise read active window
        elements: list[dict[str, Any]] = []
        text_content = ""

        if target:
            element = ctrl.find_element(name=target)
            if element is None:
                element = ctrl.find_element(automation_id=target)
            if element is not None:
                text_content = element.value or element.name
                elements.append({
                    "name": element.name,
                    "control_type": element.control_type,
                    "automation_id": element.automation_id,
                    "class_name": element.class_name,
                    "position": [element.x, element.y],
                    "size": [element.width, element.height],
                    "value": element.value,
                    "enabled": element.is_enabled,
                    "visible": element.is_visible,
                })
        else:
            # Read focused element text
            text_content = ctrl.read_text()
            # Enumerate top-level windows
            all_windows = ctrl.get_all_windows(visible_only=True)
            elements = [
                {
                    "title": w.title,
                    "class_name": w.class_name,
                    "process": w.process_name,
                    "rect": list(w.rect),
                }
                for w in all_windows[:20]  # Limit to avoid huge payload
            ]

        return {
            "ok": True,
            "text_content": text_content,
            "window_title": window_title,
            "process_name": process_name,
            "elements": elements,
            "element_count": len(elements),
        }

    except Exception as e:
        logger.error("desktop_read failed: %s", e)
        return {"ok": False, "text_content": "", "elements": [], "error": str(e)}


async def _desktop_chain(
    steps: list[dict[str, Any]],
    stop_on_error: bool = True,
) -> dict[str, Any]:
    """Execute a chain of desktop automation steps.

    Wired to: VisionDesktopAgent.chain_execute()

    Each step is a dict with:
      - action: "click" | "type" | "open" | "screenshot" | "wait" | "hotkey"
      - target (for click/type): element description
      - text (for type): text to type
      - app (for open): app name
      - keys (for hotkey): list of keys like ["ctrl", "c"]
      - seconds (for wait): float

    Example:
      [{"action": "open", "app": "notepad"},
       {"action": "wait", "seconds": 1},
       {"action": "type", "text": "Hello, World!"}]
    """
    if not steps:
        return {"ok": False, "error": "No steps provided", "steps_completed": 0, "total_steps": 0}

    try:
        agent = _get_vision_agent()
        sim = _get_input_simulator()

        completed = 0
        errors: list[dict[str, Any]] = []

        for i, step in enumerate(steps):
            action = step.get("action", "")
            step_target = step.get("target", "")

            try:
                if action == "click":
                    await agent.click(
                        target=step_target,
                        method=step.get("method", "auto"),
                    )

                elif action == "type":
                    await _desktop_type(
                        text=step.get("text", ""),
                        target=step_target,
                    )

                elif action == "open":
                    await _desktop_open(
                        target=step.get("app", ""),
                        args=step.get("args"),
                    )

                elif action == "screenshot":
                    await _desktop_screenshot(
                        region=step.get("region"),
                        ocr=step.get("ocr", False),
                        save_path=step.get("save_path", ""),
                    )

                elif action == "hotkey":
                    keys = step.get("keys", [])
                    if keys:
                        sim.hotkey(*keys)

                elif action == "wait":
                    import asyncio
                    seconds = float(step.get("seconds", 1.0))
                    await asyncio.sleep(seconds)

                elif action == "press":
                    key = step.get("key", "")
                    if key:
                        sim.press(key)

                else:
                    errors.append({
                        "step": i,
                        "error": f"Unknown action: {action}",
                        "step_data": step,
                    })
                    if stop_on_error:
                        break
                    continue

                completed += 1

            except Exception as e:
                errors.append({
                    "step": i,
                    "error": str(e),
                    "step_data": step,
                })
                if stop_on_error:
                    break

        return {
            "ok": len(errors) == 0,
            "steps_completed": completed,
            "total_steps": len(steps),
            "errors": errors,
        }

    except Exception as e:
        logger.error("desktop_chain failed: %s", e)
        return {"ok": False, "error": str(e), "steps_completed": 0, "total_steps": len(steps)}


async def _desktop_scroll(
    direction: str = "down",
    amount: int = 3,
    x: int = 0,
    y: int = 0,
) -> dict[str, Any]:
    """Scroll mouse wheel at current position or specific coordinates.

    BUG#8 修复: 独立的高层 desktop_scroll 工具, 无需通过 computer_use 间接调用。
    Wired to: InputSimulator.scroll()
    """
    try:
        sim = _get_input_simulator()
        if not sim.available:
            return {"ok": False, "error": "InputSimulator not available"}

        # Move to position first if specified
        if x > 0 or y > 0:
            try:
                import pyautogui
                pyautogui.FAILSAFE = False
                pyautogui.moveTo(x, y, duration=0.1)
            except ImportError:
                import ctypes
                ctypes.windll.user32.SetCursorPos(x, y)

        # Calculate scroll amount (positive = up, negative = down)
        scroll_clicks = amount if direction == "up" else -amount
        result = sim.scroll(scroll_clicks)
        return {
            "ok": result.success,
            "direction": direction,
            "amount": abs(amount),
            "clicks": scroll_clicks,
            "position": [x, y] if (x > 0 or y > 0) else "current",
            "detail": result.detail,
        }
    except Exception as e:
        logger.error("desktop_scroll failed: %s", e)
        return {"ok": False, "error": str(e)}


# ── Registration ─────────────────────────────────────────────────────────


async def _computer_use(action: str, target: str = "", text: str = "",
                        x: int = 0, y: int = 0, method: str = "auto") -> dict:
    """Unified computer-use API: one tool to control everything.

    Action types:
      - click: Click a UI element (finds via UIA → OCR → coordinate)
      - type: Type text (clicks target first if specified)
      - open: Launch application
      - screenshot: Capture screen
      - read: Read active window content
      - press: Press a key combination (e.g. "ctrl+c")
      - scroll: Scroll mouse wheel
      - wait: Wait for N seconds
      - chain: Execute multiple actions as a workflow
    """
    from automation.computer_use import ComputerUse, ComputerAction
    cu = ComputerUse()
    act = ComputerAction(action=action, target=target, text=text, x=x, y=y, method=method)
    result = await cu.act(act)
    return {
        "ok": result.success,
        "action": result.action,
        "target": result.target,
        "detail": result.detail,
        "element_found": result.element_found,
        "coordinates": list(result.coordinates),
        "verification_score": result.verification_score,
        "duration_ms": result.duration_ms,
    }


def register_desktop_tools(registry: ToolRegistry) -> None:
    """Register all 7 desktop automation MCP tools."""
    tools = [
        (
            "computer_use",
            "Unified computer-use: click/type/open/screenshot/read/press/scroll/wait. UIA->OCR->coordinate priority with fuzzy matching + auto-verify. Use this for ALL desktop automation instead of individual tools.",
            {"type":"object","properties":{
                "action":{"type":"string","enum":["click","type","open","screenshot","read","press","scroll","wait"]},
                "target":{"type":"string","default":"","description":"UI element name or coordinate. Supports fuzzy matching."},
                "text":{"type":"string","default":"","description":"Text to type (for action=type)."},
                "x":{"type":"integer","default":0},"y":{"type":"integer","default":0},
                "method":{"type":"string","default":"auto","enum":["auto","uia","ocr","coordinate"]},
            },"required":["action"]},
            _computer_use,
        ),
        (
            "desktop_screenshot",
            "Capture screenshot with optional OCR analysis. Returns base64 image + OCR text + resolution.",
            {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Screenshot region as [left, top, right, bottom]. Omit for full screen.",
                    },
                    "ocr": {
                        "type": "boolean",
                        "default": True,
                        "description": "Run OCR on the screenshot to extract text.",
                    },
                    "save_path": {
                        "type": "string",
                        "default": "",
                        "description": "Optional file path to save the screenshot PNG.",
                    },
                },
                "required": [],
            },
            _desktop_screenshot,
        ),
        (
            "desktop_click",
            "Click a UI element by name (UIA), visible text (OCR), or raw screen coordinates (x, y).",
            {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Element name, automation ID, control type, or visible text to click.",
                    },
                    "method": {
                        "type": "string",
                        "default": "auto",
                        "enum": ["auto", "uia", "ocr", "coordinate"],
                        "description": "Click method: auto (try UIA then OCR), uia (accessibility tree), ocr (screen text), coordinate (raw x,y).",
                    },
                    "x": {
                        "type": "integer",
                        "description": "Raw X coordinate (used when method=coordinate).",
                    },
                    "y": {
                        "type": "integer",
                        "description": "Raw Y coordinate (used when method=coordinate).",
                    },
                },
                "required": [],
            },
            _desktop_click,
        ),
        (
            "desktop_type",
            "Type text into the currently focused element. Optionally click a target element first to focus it.",
            {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to type.",
                    },
                    "target": {
                        "type": "string",
                        "default": "",
                        "description": "Optional: element name/description to click before typing (to focus).",
                    },
                },
                "required": ["text"],
            },
            _desktop_type,
        ),
        (
            "desktop_open",
            "Open an application, file, or URL by name or path. Supports common apps (notepad, chrome, vscode, etc.).",
            {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "App name (e.g. 'notepad', 'chrome'), file path, or URL to open.",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional command-line arguments for the application.",
                    },
                },
                "required": ["target"],
            },
            _desktop_open,
        ),
        (
            "desktop_read",
            "Read text content from the active window or a specific UI element. Returns window title, text, and element list.",
            {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "default": "",
                        "description": "Optional: specific element name/ID to read. Omit to read active window + list all windows.",
                    },
                    "method": {
                        "type": "string",
                        "default": "uia",
                        "enum": ["uia"],
                        "description": "Reading method (currently UIA only).",
                    },
                },
                "required": [],
            },
            _desktop_read,
        ),
        (
            "desktop_chain",
            "Execute a chain of desktop automation steps. Supports: click, type, open, screenshot, hotkey, wait, press.",
            {
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "array",
                        "description": "List of action steps. Each step has 'action' field plus action-specific params.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {
                                    "type": "string",
                                    "enum": ["click", "type", "open", "screenshot", "hotkey", "wait", "press"],
                                },
                            },
                            "required": ["action"],
                        },
                    },
                    "stop_on_error": {
                        "type": "boolean",
                        "default": True,
                        "description": "Stop executing remaining steps if any step fails.",
                    },
                },
                "required": ["steps"],
            },
            _desktop_chain,
        ),
        (
            "desktop_scroll",
            "Scroll mouse wheel up/down at current position or specific coordinates. BUG#8: dedicated scroll API — no need to use computer_use for scrolling.",
            {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "default": "down",
                        "enum": ["up", "down"],
                        "description": "Scroll direction: up (toward top of document) or down (toward bottom).",
                    },
                    "amount": {
                        "type": "integer",
                        "default": 3,
                        "description": "Number of scroll clicks (each click ~1 line). Positive integer, default 3.",
                    },
                    "x": {
                        "type": "integer",
                        "default": 0,
                        "description": "X coordinate to move mouse to before scrolling. Omit to scroll at current position.",
                    },
                    "y": {
                        "type": "integer",
                        "default": 0,
                        "description": "Y coordinate to move mouse to before scrolling. Omit to scroll at current position.",
                    },
                },
                "required": [],
            },
            _desktop_scroll,
        ),
    ]

    for name, desc, params, handler in tools:
        registry.register(
            name=name,
            description=desc,
            parameters=params,
            handler=handler,
            category="desktop",
        )
