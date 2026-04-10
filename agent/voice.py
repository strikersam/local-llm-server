"""agent/voice.py — Voice Command Interface

Hands-free agent interaction: record audio from the microphone, transcribe
it to text via Whisper, and return the transcript for use as a prompt.

Two transcription backends (auto-selected):
  1. Whisper REST API  — set WHISPER_BASE_URL env var to any OpenAI-compatible
                         transcription endpoint (e.g. a local whisper.cpp server)
  2. Local whisper     — requires ``pip install openai-whisper``

When neither is available the interface runs in *stub mode*: recording and
transcription calls succeed but return empty text with source="stub".

Audio recording requires: ``pip install pyaudio``
"""
from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass
from typing import Any

log = logging.getLogger("qwen-voice")

_PYAUDIO_HINT = "pip install pyaudio"
_WHISPER_HINT = "pip install openai-whisper  OR  set WHISPER_BASE_URL"


@dataclass
class TranscriptionResult:
    text: str
    confidence: float   # 0.0 – 1.0
    duration_s: float
    source: str         # "whisper-api" | "whisper-local" | "stub"

    def as_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "duration_s": self.duration_s,
            "source": self.source,
        }


class VoiceCommandInterface:
    """Record → transcribe → return text for hands-free agent prompting.

    Usage::

        vc = VoiceCommandInterface()
        result = vc.listen_and_transcribe(duration_s=5.0)
        if result.text:
            agent.chat(result.text)
    """

    def __init__(self) -> None:
        self._whisper_url = os.environ.get("WHISPER_BASE_URL", "").rstrip("/")
        self._mic_available = self._check_pyaudio()

    # ------------------------------------------------------------------
    # Capability flags
    # ------------------------------------------------------------------

    def _check_pyaudio(self) -> bool:
        try:
            import pyaudio  # noqa: F401
            return True
        except ImportError:
            log.info("pyaudio not installed — microphone recording unavailable (%s)", _PYAUDIO_HINT)
            return False

    @property
    def mic_available(self) -> bool:
        return self._mic_available

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(self, duration_s: float = 5.0) -> bytes:
        """Record *duration_s* seconds of audio. Returns raw PCM bytes (int16 LE, 16 kHz mono)."""
        if not self._mic_available:
            log.warning("Cannot record: pyaudio not installed")
            return b""
        import pyaudio

        sample_rate = 16_000
        chunk = 1_024
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            input=True,
            frames_per_buffer=chunk,
        )
        n_chunks = int(sample_rate / chunk * duration_s)
        frames: list[bytes] = [stream.read(chunk) for _ in range(n_chunks)]
        stream.stop_stream()
        stream.close()
        p.terminate()
        return b"".join(frames)

    def transcribe(self, audio_bytes: bytes) -> TranscriptionResult:
        """Transcribe raw PCM *audio_bytes* to text."""
        if not audio_bytes:
            return _stub_result()
        if self._whisper_url:
            return self._transcribe_api(audio_bytes)
        return self._transcribe_local(audio_bytes)

    def listen_and_transcribe(self, duration_s: float = 5.0) -> TranscriptionResult:
        """Record then transcribe in one call."""
        audio = self.record(duration_s)
        return self.transcribe(audio)

    # ------------------------------------------------------------------
    # Transcription backends
    # ------------------------------------------------------------------

    def _transcribe_api(self, audio_bytes: bytes) -> TranscriptionResult:
        try:
            import httpx

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                tmp = f.name
            with open(tmp, "rb") as af:
                resp = httpx.post(
                    f"{self._whisper_url}/v1/audio/transcriptions",
                    files={"file": ("audio.wav", af, "audio/wav")},
                    data={"model": "whisper-1"},
                    timeout=30.0,
                )
            resp.raise_for_status()
            text = resp.json().get("text", "").strip()
            return TranscriptionResult(text=text, confidence=0.9, duration_s=0.0, source="whisper-api")
        except Exception as exc:
            log.warning("Whisper API transcription failed: %s", exc)
            return _stub_result()

    def _transcribe_local(self, audio_bytes: bytes) -> TranscriptionResult:
        try:
            import numpy as np
            import whisper  # type: ignore[import]

            audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32_768.0
            model = whisper.load_model("base")
            result = model.transcribe(audio)
            text = result.get("text", "").strip()
            return TranscriptionResult(text=text, confidence=0.85, duration_s=0.0, source="whisper-local")
        except ImportError:
            log.info("openai-whisper not installed — using stub (%s)", _WHISPER_HINT)
            return _stub_result()
        except Exception as exc:
            log.warning("Local whisper transcription failed: %s", exc)
            return _stub_result()


def _stub_result() -> TranscriptionResult:
    return TranscriptionResult(text="", confidence=0.0, duration_s=0.0, source="stub")
