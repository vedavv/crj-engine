"""Pitch detection — extract F0 contour from audio using CREPE or pYIN."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class PitchAlgorithm(Enum):
    CREPE = "crepe"
    PYIN = "pyin"


@dataclass
class PitchFrame:
    """A single frame of pitch detection output."""

    timestamp_ms: float
    frequency_hz: float
    confidence: float


@dataclass
class PitchContour:
    """Complete pitch contour from an audio analysis."""

    frames: list[PitchFrame]
    algorithm: PitchAlgorithm
    sample_rate: int
    hop_ms: float

    @property
    def timestamps(self) -> np.ndarray:
        return np.array([f.timestamp_ms for f in self.frames])

    @property
    def frequencies(self) -> np.ndarray:
        return np.array([f.frequency_hz for f in self.frames])

    @property
    def confidences(self) -> np.ndarray:
        return np.array([f.confidence for f in self.frames])

    def filter_by_confidence(self, min_confidence: float = 0.5) -> PitchContour:
        """Return a new PitchContour with only frames above the confidence threshold."""
        filtered = [f for f in self.frames if f.confidence >= min_confidence]
        return PitchContour(
            frames=filtered,
            algorithm=self.algorithm,
            sample_rate=self.sample_rate,
            hop_ms=self.hop_ms,
        )


def detect_pitch_crepe(
    audio: np.ndarray,
    sr: int = 16000,
    hop_ms: float = 10.0,
    min_confidence: float = 0.5,
) -> PitchContour:
    """Detect pitch using CREPE (via torchcrepe).

    Args:
        audio: Mono audio samples as float32 numpy array.
        sr: Sample rate of the audio.
        hop_ms: Hop size in milliseconds between frames.
        min_confidence: Minimum confidence threshold for voiced frames.

    Returns:
        PitchContour with detected F0 values.
    """
    import torch
    import torchcrepe

    # Convert to torch tensor
    audio_tensor = torch.tensor(audio).unsqueeze(0).float()

    hop_length = int(sr * hop_ms / 1000)

    # Run CREPE pitch detection
    pitch, periodicity = torchcrepe.predict(
        audio_tensor,
        sr,
        hop_length=hop_length,
        fmin=50,   # Hz — below typical vocal range
        fmax=2000,  # Hz — above typical vocal range
        model="full",
        batch_size=256,
        return_periodicity=True,
    )

    # Convert to numpy
    pitch_np = pitch.squeeze().numpy()
    confidence_np = periodicity.squeeze().numpy()

    # Build frames
    frames = []
    for i in range(len(pitch_np)):
        timestamp = i * hop_ms
        freq = float(pitch_np[i])
        conf = float(confidence_np[i])

        # Mark unvoiced frames (below confidence) with freq = 0
        if conf < min_confidence:
            freq = 0.0

        frames.append(PitchFrame(
            timestamp_ms=timestamp,
            frequency_hz=freq,
            confidence=conf,
        ))

    return PitchContour(
        frames=frames,
        algorithm=PitchAlgorithm.CREPE,
        sample_rate=sr,
        hop_ms=hop_ms,
    )


def detect_pitch_pyin(
    audio: np.ndarray,
    sr: int = 16000,
    hop_ms: float = 10.0,
    min_confidence: float = 0.5,
) -> PitchContour:
    """Detect pitch using pYIN (via librosa).

    Args:
        audio: Mono audio samples as float32 numpy array.
        sr: Sample rate of the audio.
        hop_ms: Hop size in milliseconds between frames.
        min_confidence: Minimum confidence threshold.

    Returns:
        PitchContour with detected F0 values.
    """
    import librosa

    hop_length = int(sr * hop_ms / 1000)

    f0, voiced_flag, voiced_probs = librosa.pyin(
        audio,
        fmin=50,
        fmax=2000,
        sr=sr,
        hop_length=hop_length,
    )

    frames = []
    for i in range(len(f0)):
        timestamp = i * hop_ms
        freq = float(f0[i]) if not np.isnan(f0[i]) else 0.0
        if voiced_probs is not None:
            conf = float(voiced_probs[i])
        else:
            conf = 1.0 if voiced_flag[i] else 0.0

        if conf < min_confidence:
            freq = 0.0

        frames.append(PitchFrame(
            timestamp_ms=timestamp,
            frequency_hz=freq,
            confidence=conf,
        ))

    return PitchContour(
        frames=frames,
        algorithm=PitchAlgorithm.PYIN,
        sample_rate=sr,
        hop_ms=hop_ms,
    )


def detect_pitch(
    audio: np.ndarray,
    sr: int = 16000,
    algorithm: PitchAlgorithm = PitchAlgorithm.CREPE,
    **kwargs,
) -> PitchContour:
    """Detect pitch using the specified algorithm.

    This is the main entry point for pitch detection.
    """
    if algorithm == PitchAlgorithm.CREPE:
        return detect_pitch_crepe(audio, sr, **kwargs)
    elif algorithm == PitchAlgorithm.PYIN:
        return detect_pitch_pyin(audio, sr, **kwargs)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")
