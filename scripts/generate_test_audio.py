#!/usr/bin/env python3
"""Generate synthetic test audio files with known frequencies for pipeline validation."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "peer-test" / "audio"
SAMPLE_RATE = 44100


def generate_tone(freq_hz: float, duration_s: float, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Generate a pure sine wave at the given frequency."""
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    # Add slight fade in/out to avoid clicks
    audio = np.sin(2 * np.pi * freq_hz * t).astype(np.float32)
    fade_len = int(sr * 0.02)  # 20ms fade
    audio[:fade_len] *= np.linspace(0, 1, fade_len)
    audio[-fade_len:] *= np.linspace(1, 0, fade_len)
    return audio


def main():
    import soundfile as sf

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sa_hz = 261.63  # C4

    # Test 1: Single Sa tone (3 seconds)
    sa_tone = generate_tone(sa_hz, 3.0)
    sa_path = OUTPUT_DIR / "test_sa_261hz.wav"
    sf.write(str(sa_path), sa_tone, SAMPLE_RATE)
    print(f"Generated: {sa_path} (Sa = {sa_hz} Hz, 3s)")

    # Test 2: Shankarabharanam ascending scale (Sa Ri Ga Ma Pa Dha Ni Sa')
    scale_cents = [0, 200, 400, 500, 700, 900, 1100, 1200]
    swara_names = ["Sa", "Ri2", "Ga3", "Ma1", "Pa", "Dha2", "Ni3", "Sa'"]
    note_duration = 0.75  # seconds per note

    scale_audio = np.array([], dtype=np.float32)
    silence = np.zeros(int(SAMPLE_RATE * 0.1), dtype=np.float32)  # 100ms gap

    for cents, name in zip(scale_cents, swara_names):
        freq = sa_hz * (2 ** (cents / 1200))
        tone = generate_tone(freq, note_duration)
        scale_audio = np.concatenate([scale_audio, tone, silence])
        print(f"  {name}: {freq:.1f} Hz")

    scale_path = OUTPUT_DIR / "test_shankarabharanam_scale.wav"
    sf.write(str(scale_path), scale_audio, SAMPLE_RATE)
    print(f"Generated: {scale_path} (Shankarabharanam scale, {len(scale_audio)/SAMPLE_RATE:.1f}s)")

    # Test 3: Pa drone (Sa + Pa together, 5 seconds)
    t = np.linspace(0, 5.0, int(SAMPLE_RATE * 5.0), endpoint=False)
    pa_hz = sa_hz * 1.5
    drone = (0.5 * np.sin(2 * np.pi * sa_hz * t) + 0.3 * np.sin(2 * np.pi * pa_hz * t)).astype(np.float32)
    drone_path = OUTPUT_DIR / "test_sa_pa_drone.wav"
    sf.write(str(drone_path), drone, SAMPLE_RATE)
    print(f"Generated: {drone_path} (Sa+Pa drone, 5s)")

    print(f"\nAll test files in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
