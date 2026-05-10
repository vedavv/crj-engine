"""Tests for SRT parsing and separator-based unit mapping."""

import numpy as np

from crj_engine.tala.srt_sync import (
    build_srt_units,
    detect_separator_events,
    parse_srt,
)


def _build_tone(sr: int, hz: float, duration_s: float, amp: float = 0.4) -> np.ndarray:
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    return (amp * np.sin(2 * np.pi * hz * t)).astype(np.float32)


def test_parse_srt_blocks():
    srt = (
        "1\n"
        "00:00:00,000 --> 00:00:02,000\n"
        "First line\n\n"
        "2\n"
        "00:00:02,000 --> 00:00:04,000\n"
        "Second line\n"
    )
    entries = parse_srt(srt)
    assert len(entries) == 2
    assert entries[0].index == 1
    assert entries[1].text == "Second line"


def test_detect_silence_separator_mode():
    sr = 16000
    a = _build_tone(sr, 440.0, 0.8)
    silence = np.zeros(int(0.7 * sr), dtype=np.float32)
    b = _build_tone(sr, 440.0, 0.8)
    audio = np.concatenate([a, silence, b])

    events = detect_separator_events(audio, sr, mode="silence", min_silence_ms=400.0)
    assert len(events) >= 1
    assert events[0].event_type == "silence"


def test_build_srt_units_uses_separator_boundaries():
    srt = (
        "1\n00:00:00,000 --> 00:00:01,000\nOne\n\n"
        "2\n00:00:01,000 --> 00:00:02,000\nTwo\n\n"
        "3\n00:00:02,000 --> 00:00:03,000\nThree\n"
    )
    entries = parse_srt(srt)

    class Wrap:
        def __init__(self, event_type, end_ms):
            self.event_type = event_type
            self.start_ms = end_ms - 50
            self.end_ms = end_ms
            self.confidence = 0.9

    events = [Wrap("double_beep", 900.0), Wrap("bell", 1950.0)]
    units = build_srt_units(entries, events, duration_ms=3000.0)

    assert len(units) == 3
    assert abs(units[0].end_ms - 900.0) < 1e-3
    assert abs(units[1].end_ms - 1950.0) < 1e-3
    assert units[2].end_ms == 3000.0
