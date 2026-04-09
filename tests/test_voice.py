"""Tests for agent/voice.py — Voice Command Interface (stub-mode tests)."""
from agent.voice import TranscriptionResult, VoiceCommandInterface, _stub_result


def test_voice_interface_created():
    vc = VoiceCommandInterface()
    assert isinstance(vc.mic_available, bool)


def test_transcribe_empty_audio():
    vc = VoiceCommandInterface()
    result = vc.transcribe(b"")
    assert isinstance(result, TranscriptionResult)
    assert result.text == ""
    assert result.source == "stub"


def test_stub_result():
    r = _stub_result()
    assert r.text == ""
    assert r.confidence == 0.0
    assert r.source == "stub"


def test_as_dict():
    r = TranscriptionResult(text="hello", confidence=0.9, duration_s=3.0, source="whisper-api")
    d = r.as_dict()
    assert d["text"] == "hello"
    assert d["source"] == "whisper-api"
    assert "confidence" in d


def test_listen_transcribe_without_mic():
    vc = VoiceCommandInterface()
    if vc.mic_available:
        # If mic is available we can't easily test without hardware
        return
    result = vc.listen_and_transcribe(duration_s=0.1)
    assert result.source == "stub"
    assert result.text == ""
