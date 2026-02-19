"""Audio I/O — load, normalize, and convert audio files for processing."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

# Default config path
_CONFIGS_DIR = Path(__file__).resolve().parents[3] / "configs"


def load_config(config_name: str = "tuning.json") -> dict:
    """Load a JSON config file from the configs/ directory."""
    config_path = _CONFIGS_DIR / config_name
    with open(config_path) as f:
        return json.load(f)


def _load_via_pydub(
    file_path: Path, fmt: str, target_sr: int,
) -> tuple[np.ndarray, int]:
    """Load audio via pydub (requires ffmpeg). Works for MP3, M4A, AAC, OGG, etc."""
    import io

    import librosa
    import soundfile as sf
    from pydub import AudioSegment

    seg = AudioSegment.from_file(str(file_path), format=fmt)
    seg = seg.set_channels(1)  # mono
    buf = io.BytesIO()
    seg.export(buf, format="wav")
    buf.seek(0)
    audio, sr_native = sf.read(buf, dtype="float32")
    if target_sr and target_sr != sr_native:
        audio = librosa.resample(audio, orig_sr=sr_native, target_sr=target_sr)
        sr_native = target_sr
    return audio.astype(np.float32), sr_native


# Formats that need pydub/ffmpeg conversion
_PYDUB_FORMATS: dict[str, str] = {
    ".mp3": "mp3",
    ".m4a": "m4a",
    ".aac": "aac",
    ".ogg": "ogg",
    ".wma": "wma",
    ".webm": "webm",
}


def load_audio(file_path: str | Path, target_sr: int = 16000) -> tuple[np.ndarray, int]:
    """Load an audio file and return (samples, sample_rate).

    Handles WAV, MP3, M4A, AAC, FLAC, OGG, WebM. Converts to mono and resamples to target_sr.

    Args:
        file_path: Path to the audio file.
        target_sr: Target sample rate in Hz (default 16kHz for pitch detection).

    Returns:
        Tuple of (audio_samples as float32 numpy array, sample_rate).
    """
    import librosa

    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    suffix = file_path.suffix.lower()

    # MP3, M4A, AAC, OGG, WMA — convert via pydub (ffmpeg)
    if suffix in _PYDUB_FORMATS:
        return _load_via_pydub(file_path, _PYDUB_FORMATS[suffix], target_sr)

    # WAV, FLAC — librosa handles natively via soundfile
    audio, sr = librosa.load(str(file_path), sr=target_sr, mono=True)
    return audio.astype(np.float32), sr


def get_duration(audio: np.ndarray, sr: int) -> float:
    """Return audio duration in seconds."""
    return len(audio) / sr
