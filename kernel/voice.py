"""Voice Interface — WebRTC real-time voice skeleton (Gap: 语音/实时).

Provides speech-to-text and text-to-speech capabilities.
Extensible to full WebRTC voice chat.

Backends:
  - Whisper (local): OpenAI Whisper for STT
  - Edge TTS (free): Microsoft Edge TTS for TTS
  - WebRTC (planned): Real-time voice via aiortc

Usage:
    voice = VoiceInterface()
    text = await voice.speech_to_text(audio_bytes)
    audio = await voice.text_to_speech("Hello, world!")
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sclerotium.voice")


@dataclass(frozen=True)
class VoiceConfig:
    """Voice configuration (immutable)."""
    stt_backend: str = "whisper"     # "whisper" | "azure" | "google"
    tts_backend: str = "edge"       # "edge" | "openai" | "elevenlabs"
    language: str = "zh-CN"
    voice: str = "zh-CN-XiaoxiaoNeural"  # Edge TTS voice
    speed: float = 1.0


class VoiceInterface:
    """Speech-to-text and text-to-speech interface.

    Usage:
        voice = VoiceInterface()
        text = await voice.speech_to_text(b"audio data...")
        audio_path = await voice.text_to_speech("你好，世界！")
    """

    def __init__(self, config: VoiceConfig | None = None) -> None:
        self.config = config or VoiceConfig()
        self._whisper_model = None

    # ── Speech-to-Text ─────────────────────────────────────────────────

    async def speech_to_text(self, audio_bytes: bytes, language: str = "") -> str:
        """Convert speech audio to text.

        Args:
            audio_bytes: WAV/MP3 audio data
            language: Language code (auto-detect if empty)

        Returns:
            Transcribed text
        """
        if self.config.stt_backend == "whisper":
            return await self._stt_whisper(audio_bytes, language or self.config.language)

        logger.warning("STT backend '%s' not available", self.config.stt_backend)
        return ""

    async def _stt_whisper(self, audio_bytes: bytes, language: str) -> str:
        """Use local Whisper model for STT."""
        try:
            import whisper

            if self._whisper_model is None:
                self._whisper_model = whisper.load_model("base")

            # Write temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                tmp_path = f.name

            try:
                result = self._whisper_model.transcribe(
                    tmp_path,
                    language=language.split("-")[0] if language else None,
                )
                return result.get("text", "").strip()
            finally:
                os.unlink(tmp_path)

        except ImportError:
            logger.info("Whisper not installed. Install: pip install openai-whisper")
            return ""
        except Exception as e:
            logger.error("Whisper STT failed: %s", e)
            return ""

    # ── Text-to-Speech ─────────────────────────────────────────────────

    async def text_to_speech(
        self, text: str, output_path: str = "",
    ) -> str:
        """Convert text to speech audio.

        Args:
            text: Text to speak
            output_path: Output file path (auto-generated if empty)

        Returns:
            Path to audio file
        """
        if self.config.tts_backend == "edge":
            return await self._tts_edge(text, output_path)
        if self.config.tts_backend == "openai":
            return await self._tts_openai(text, output_path)

        logger.warning("TTS backend '%s' not available", self.config.tts_backend)
        return ""

    async def _tts_edge(self, text: str, output_path: str) -> str:
        """Use Microsoft Edge TTS (free, no API key)."""
        try:
            import edge_tts

            if not output_path:
                output_path = tempfile.mktemp(suffix=".mp3")

            communicate = edge_tts.Communicate(
                text=text,
                voice=self.config.voice,
                rate=f"{int((self.config.speed - 1) * 100):+d}%",
            )
            await communicate.save(output_path)

            logger.info("Edge TTS saved to %s", output_path)
            return output_path

        except ImportError:
            logger.info("edge-tts not installed. Install: pip install edge-tts")
            return ""
        except Exception as e:
            logger.error("Edge TTS failed: %s", e)
            return ""

    async def _tts_openai(self, text: str, output_path: str) -> str:
        """Use OpenAI TTS API."""
        try:
            import aiohttp

            api_key = os.environ.get("OPENAI_API_KEY", "")
            if not api_key:
                logger.warning("OPENAI_API_KEY not set")
                return ""

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/audio/speech",
                    json={
                        "model": "tts-1",
                        "voice": "alloy",
                        "input": text,
                        "speed": self.config.speed,
                    },
                    headers={"Authorization": f"Bearer {api_key}"},
                ) as resp:
                    if resp.status == 200:
                        audio_data = await resp.read()
                        if not output_path:
                            output_path = tempfile.mktemp(suffix=".mp3")
                        with open(output_path, "wb") as f:
                            f.write(audio_data)
                        return output_path

            return ""

        except Exception as e:
            logger.error("OpenAI TTS failed: %s", e)
            return ""

    # ── Convenience ───────────────────────────────────────────────────

    async def speak(self, text: str) -> bool:
        """Speak text aloud (TTS + play)."""
        audio_path = await self.text_to_speech(text)
        if not audio_path:
            return False

        try:
            # Try to play audio
            import platform
            import subprocess

            system = platform.system()
            if system == "Windows":
                subprocess.Popen(
                    ["powershell", "-c",
                     f"(New-Object Media.SoundPlayer '{audio_path}').PlaySync()"],
                )
            elif system == "Darwin":
                subprocess.Popen(["afplay", audio_path])
            else:
                subprocess.Popen(["aplay", audio_path])

            return True
        except Exception as e:
            logger.warning("Audio playback failed: %s", e)
            return False
