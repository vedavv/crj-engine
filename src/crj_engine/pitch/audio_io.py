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


def load_audio(file_path: str | Path, target_sr: int = 16000) -> tuple[np.ndarray, int]:
    """Load an audio file and return (samples, sample_rate).

    Handles WAV, MP3, FLAC. Converts to mono and resamples to target_sr.

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

    # For MP3: convert to WAV via pydub (ffmpeg) first, then load with librosa
    if suffix == ".mp3":
        import io
        import soundfile as sf
        from pydub import AudioSegment

        seg = AudioSegment.from_mp3(str(file_path))
        seg = seg.set_channels(1)  # mono
        buf = io.BytesIO()
        seg.export(buf, format="wav")
        buf.seek(0)
        audio, sr_native = sf.read(buf, dtype="float32")
        if target_sr and target_sr != sr_native:
            audio = librosa.resample(audio, orig_sr=sr_native, target_sr=target_sr)
            sr_native = target_sr
        return audio.astype(np.float32), sr_native

    # WAV, FLAC — librosa handles natively via soundfile
    audio, sr = librosa.load(str(file_path), sr=target_sr, mono=True)
    return audio.astype(np.float32), sr


def get_duration(audio: np.ndarray, sr: int) -> float:
    """Return audio duration in seconds."""
    return len(audio) / sr
