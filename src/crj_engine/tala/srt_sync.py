"""SRT sync utilities driven by audio separator events.

Provides:
- SRT parsing
- Separator detection from audio (silence, bell, double-beep)
- Mapping separator boundaries to SRT units for playback progression
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np


@dataclass
class SeparatorEvent:
    event_type: str
    start_ms: float
    end_ms: float
    confidence: float


@dataclass
class SRTEntry:
    index: int
    start_ms: float
    end_ms: float
    text: str


@dataclass
class SRTUnit:
    index: int
    text: str
    start_ms: float
    end_ms: float
    source: str


_TS_RE = re.compile(
    r"(?P<h1>\d{2}):(?P<m1>\d{2}):(?P<s1>\d{2}),(?P<ms1>\d{3})\s*-->\s*"
    r"(?P<h2>\d{2}):(?P<m2>\d{2}):(?P<s2>\d{2}),(?P<ms2>\d{3})"
)


def _ts_to_ms(h: str, m: str, s: str, ms: str) -> float:
    return (
        int(h) * 3600 * 1000
        + int(m) * 60 * 1000
        + int(s) * 1000
        + int(ms)
    )


def parse_srt(srt_content: str) -> list[SRTEntry]:
    """Parse SRT text into entries.

    Accepts canonical SRT blocks. Keeps entries with valid time rows.
    """
    if not srt_content or not srt_content.strip():
        return []

    blocks = re.split(r"\r?\n\s*\r?\n", srt_content.strip())
    entries: list[SRTEntry] = []

    for b in blocks:
        lines = [ln.strip("\ufeff ") for ln in b.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue

        ptr = 0
        try:
            idx = int(lines[0])
            ptr = 1
        except ValueError:
            idx = len(entries) + 1

        match = _TS_RE.search(lines[ptr])
        if not match:
            continue

        start_ms = _ts_to_ms(
            match.group("h1"),
            match.group("m1"),
            match.group("s1"),
            match.group("ms1"),
        )
        end_ms = _ts_to_ms(
            match.group("h2"),
            match.group("m2"),
            match.group("s2"),
            match.group("ms2"),
        )
        text = " ".join(lines[ptr + 1 :]).strip()
        if end_ms <= start_ms:
            continue

        entries.append(SRTEntry(index=idx, start_ms=start_ms, end_ms=end_ms, text=text))

    return entries


def _find_regions(mask: np.ndarray, frame_ms: float, min_len_ms: float) -> list[tuple[float, float]]:
    regions: list[tuple[float, float]] = []
    start = -1
    for i, val in enumerate(mask):
        if val and start < 0:
            start = i
        if not val and start >= 0:
            end = i - 1
            dur = (end - start + 1) * frame_ms
            if dur >= min_len_ms:
                regions.append((start * frame_ms, (end + 1) * frame_ms))
            start = -1
    if start >= 0:
        end = len(mask) - 1
        dur = (end - start + 1) * frame_ms
        if dur >= min_len_ms:
            regions.append((start * frame_ms, (end + 1) * frame_ms))
    return regions


def _detect_silence_events(
    audio: np.ndarray,
    sr: int,
    min_silence_ms: float,
    silence_db_threshold: float,
) -> list[SeparatorEvent]:
    frame_len = max(1, int(0.02 * sr))
    hop = max(1, int(0.01 * sr))
    if len(audio) < frame_len:
        return []

    n_frames = 1 + (len(audio) - frame_len) // hop
    rms = np.empty(n_frames, dtype=np.float32)
    for i in range(n_frames):
        start = i * hop
        seg = audio[start : start + frame_len]
        rms[i] = float(np.sqrt(np.mean(seg * seg) + 1e-12))

    thresh = 10 ** (silence_db_threshold / 20.0)
    silent = rms <= thresh
    frame_ms = (hop / sr) * 1000.0

    events: list[SeparatorEvent] = []
    for st, en in _find_regions(silent, frame_ms, min_silence_ms):
        dur = en - st
        conf = min(0.99, 0.55 + (dur / max(min_silence_ms, 1.0)) * 0.2)
        events.append(SeparatorEvent(
            event_type="silence",
            start_ms=round(st, 2),
            end_ms=round(en, 2),
            confidence=round(conf, 3),
        ))
    return events


def _detect_tonal_markers(audio: np.ndarray, sr: int) -> list[SeparatorEvent]:
    """Detect tonal separator markers and classify as bell/beep/double-beep."""
    import librosa

    if len(audio) < int(0.1 * sr):
        return []

    y = np.asarray(audio, dtype=np.float32)
    y = y / max(1e-9, float(np.max(np.abs(y))))

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    if onset_env.size == 0:
        return []

    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_env,
        sr=sr,
        units="frames",
        backtrack=False,
        pre_max=2,
        post_max=2,
        pre_avg=6,
        post_avg=6,
        delta=0.25,
        wait=2,
    )

    if onset_frames.size == 0:
        return []

    times_ms = librosa.frames_to_time(onset_frames, sr=sr) * 1000.0

    classified: list[SeparatorEvent] = []
    win = int(0.12 * sr)
    for ms in times_ms:
        center = int((ms / 1000.0) * sr)
        left = max(0, center - win // 3)
        right = min(len(y), center + win)
        seg = y[left:right]
        if len(seg) < 64:
            continue

        spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
        freqs = np.fft.rfftfreq(len(seg), d=1.0 / sr)
        if spec.size < 2:
            continue

        dom_idx = int(np.argmax(spec[1:]) + 1)
        dom_hz = float(freqs[dom_idx])

        env = np.abs(seg)
        pk = float(np.max(env))
        if pk < 0.08:
            continue

        above = np.where(env >= (pk * 0.3))[0]
        if above.size:
            decay_ms = ((above[-1] - above[0]) / sr) * 1000.0
        else:
            decay_ms = 0.0

        start_ms = ms
        end_ms = ms + max(80.0, min(450.0, decay_ms))

        if 900.0 <= dom_hz <= 2600.0 and decay_ms <= 230.0:
            classified.append(SeparatorEvent("beep", start_ms, end_ms, 0.8))
        elif 350.0 <= dom_hz <= 1300.0 and decay_ms >= 160.0:
            classified.append(SeparatorEvent("bell", start_ms, end_ms, 0.75))

    # Merge consecutive beeps into double-beep
    merged: list[SeparatorEvent] = []
    i = 0
    while i < len(classified):
        ev = classified[i]
        if ev.event_type == "beep" and i + 1 < len(classified):
            nxt = classified[i + 1]
            gap = nxt.start_ms - ev.end_ms
            if nxt.event_type == "beep" and 80.0 <= gap <= 420.0:
                merged.append(SeparatorEvent(
                    event_type="double_beep",
                    start_ms=round(ev.start_ms, 2),
                    end_ms=round(nxt.end_ms, 2),
                    confidence=0.9,
                ))
                i += 2
                continue
        merged.append(SeparatorEvent(
            event_type=ev.event_type,
            start_ms=round(ev.start_ms, 2),
            end_ms=round(ev.end_ms, 2),
            confidence=round(ev.confidence, 3),
        ))
        i += 1

    return merged


def detect_separator_events(
    audio: np.ndarray,
    sr: int,
    mode: str = "auto",
    min_silence_ms: float = 450.0,
    silence_db_threshold: float = -40.0,
) -> list[SeparatorEvent]:
    """Detect separator events from raw audio.

    Modes:
      - silence: silence-only boundaries
      - bell: bell-only boundaries
      - double_beep: double-beep-only boundaries
      - auto: prioritize double_beep/bell and include long silences as fallback
    """
    mode = (mode or "auto").strip().lower()

    silence_events = _detect_silence_events(
        audio,
        sr,
        min_silence_ms=min_silence_ms,
        silence_db_threshold=silence_db_threshold,
    )
    tonal = _detect_tonal_markers(audio, sr)

    if mode == "silence":
        return silence_events
    if mode == "bell":
        return [e for e in tonal if e.event_type == "bell"]
    if mode == "double_beep":
        return [e for e in tonal if e.event_type == "double_beep"]

    # Auto mode
    tonal_priority = [e for e in tonal if e.event_type in {"double_beep", "bell"}]
    all_events = tonal_priority + silence_events
    all_events.sort(key=lambda e: (e.start_ms, e.end_ms))

    # Deduplicate nearby events (keep higher-confidence one)
    deduped: list[SeparatorEvent] = []
    for e in all_events:
        if not deduped:
            deduped.append(e)
            continue
        prev = deduped[-1]
        if e.start_ms - prev.end_ms < 120.0:
            if e.confidence > prev.confidence:
                deduped[-1] = e
            continue
        deduped.append(e)

    return deduped


def build_srt_units(
    entries: list[SRTEntry],
    separator_events: list[SeparatorEvent],
    duration_ms: float,
) -> list[SRTUnit]:
    """Map SRT text entries to detected separator boundaries.

    Strategy:
    - Need N units for N SRT entries.
    - Use up to N-1 separator boundaries (event end times).
    - If separators are insufficient, fill remaining boundaries by even spacing.
    """
    if not entries:
        return []

    n = len(entries)
    event_bounds = sorted(e.end_ms for e in separator_events if 0.0 < e.end_ms < duration_ms)
    event_bounds = event_bounds[: max(0, n - 1)]

    needed = max(0, n - 1 - len(event_bounds))
    if needed > 0:
        # Evenly distribute remaining fallback boundaries where not already occupied.
        candidates = [duration_ms * (i / n) for i in range(1, n)]
        for c in candidates:
            if needed == 0:
                break
            if all(abs(c - e) > 180.0 for e in event_bounds):
                event_bounds.append(c)
                needed -= 1

    event_bounds = sorted(event_bounds)
    event_bounds = event_bounds[: max(0, n - 1)]

    boundaries = [0.0, *event_bounds, duration_ms]
    # Ensure exact size n+1 by fallback interpolation
    if len(boundaries) < n + 1:
        boundaries = [duration_ms * (i / n) for i in range(n + 1)]

    units: list[SRTUnit] = []
    for i, entry in enumerate(entries):
        st = max(0.0, boundaries[i])
        en = max(st, boundaries[i + 1])
        source = "separator" if i < len(event_bounds) else "fallback"
        units.append(SRTUnit(
            index=entry.index,
            text=entry.text,
            start_ms=round(st, 2),
            end_ms=round(en, 2),
            source=source,
        ))

    # Smooth monotonicity
    for i in range(1, len(units)):
        if units[i].start_ms < units[i - 1].end_ms:
            units[i].start_ms = units[i - 1].end_ms
        if units[i].end_ms < units[i].start_ms:
            units[i].end_ms = units[i].start_ms

    return units
