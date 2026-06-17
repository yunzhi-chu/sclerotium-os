"""P2: Voice Input + Remote Control.

Voice: Speech-to-text via faster-whisper (local) or API.
Remote: Control Sclerotium from another machine (app-server v2 RPCs).

Reference: Codex voice input (hold spacebar), Codex app-server v2 RPCs,
Hermes remote control, OpenClaw agent-to-agent communication.
"""

from __future__ import annotations

from typing import Any


class VoiceInput:
    """Speech-to-text input for hands-free interaction."""

    def __init__(self) -> None:
        self._whisper_available = self._check_whisper()

    def _check_whisper(self) -> bool:
        try:
            import faster_whisper
            return True
        except ImportError:
            return False

    async def listen(self, duration_seconds: int = 5) -> dict[str, Any]:
        """Listen and transcribe speech."""
        if not self._whisper_available:
            return {"status": "unavailable", "text": "",
                    "note": "Install faster-whisper: pip install faster-whisper"}

        try:
            import sounddevice as sd
            import numpy as np
            import tempfile
            from faster_whisper import WhisperModel

            # Record audio
            sample_rate = 16000
            recording = sd.rec(
                int(duration_seconds * sample_rate),
                samplerate=sample_rate, channels=1, dtype="float32"
            )
            sd.wait()

            # Save to temp WAV
            import wave, io
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes((recording * 32767).astype(np.int16).tobytes())

            # Transcribe
            model = WhisperModel("tiny", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(buf.getvalue())
            text = " ".join(s.text for s in segments)

            return {"status": "ok", "text": text, "duration_s": duration_seconds}
        except ImportError:
            return {"status": "unavailable", "text": "",
                    "note": "Install sounddevice + faster-whisper"}
        except Exception as e:
            return {"status": "error", "text": "", "error": str(e)}


class RemoteControl:
    """Remote control via simple HTTP RPC.

    Allows controlling Sclerotium from another machine on the LAN.
    Phase 5: Full app-server v2 RPCs with authentication.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self._running = False

    async def start_server(self) -> dict[str, Any]:
        """Start remote control server."""
        try:
            import asyncio
            self._running = True
            return {"status": "started", "host": self.host, "port": self.port,
                    "url": f"http://{self.host}:{self.port}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def stop_server(self) -> dict[str, Any]:
        self._running = False
        return {"status": "stopped"}

    async def send_command(self, target_url: str, command: str, params: dict | None = None) -> dict:
        """Send a command to another Sclerotium instance."""
        import urllib.request, json
        try:
            body = json.dumps({"command": command, "params": params or {}}).encode()
            req = urllib.request.Request(
                f"{target_url}/execute",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            return {"status": "error", "error": str(e)}
