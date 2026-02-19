#!/usr/bin/env python3
"""Quick test: run pitch detection on vkg.mp3 and map to swaras."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crj_engine.pitch.audio_io import get_duration, load_audio
from crj_engine.pitch.detector import PitchAlgorithm, detect_pitch
from crj_engine.swara.mapper import freq_to_swara, freq_to_western

AUDIO_DIR = Path(__file__).resolve().parents[1] / "data" / "peer-test" / "audio"
AUDIO_FILE = AUDIO_DIR / "test_shankarabharanam_scale.wav"
REFERENCE_SA_HZ = 261.63  # C4 — default, adjust as needed


def main():
    print(f"Loading: {AUDIO_FILE}")
    audio, sr = load_audio(AUDIO_FILE, target_sr=16000)
    duration = get_duration(audio, sr)
    print(f"Duration: {duration:.1f}s | Sample rate: {sr} Hz | Samples: {len(audio)}")

    print(f"\nRunning pYIN pitch detection...")
    contour = detect_pitch(audio, sr, algorithm=PitchAlgorithm.PYIN)
    voiced = contour.filter_by_confidence(min_confidence=0.5)

    print(f"Total frames: {len(contour.frames)}")
    print(f"Voiced frames: {len(voiced.frames)}")

    if not voiced.frames:
        print("No voiced frames detected.")
        return

    # Show first 20 voiced frames with swara mapping
    print(f"\nFirst 20 voiced frames (Sa = {REFERENCE_SA_HZ} Hz):")
    print(f"{'Time (ms)':>10} {'Freq (Hz)':>10} {'Conf':>6} {'Western':>8} {'Swara':>8} {'Script':>12}")
    print("-" * 65)

    for frame in voiced.frames[:20]:
        western = freq_to_western(frame.frequency_hz)
        swara = freq_to_swara(frame.frequency_hz, reference_sa_hz=REFERENCE_SA_HZ)

        swara_name = swara.swara_id if swara else "?"
        kannada = swara.names.get("kannada", "") if swara else ""

        print(
            f"{frame.timestamp_ms:10.0f} "
            f"{frame.frequency_hz:10.1f} "
            f"{frame.confidence:6.2f} "
            f"{western.name + str(western.octave):>8} "
            f"{swara_name:>8} "
            f"{kannada:>12}"
        )

    # Frequency distribution
    freqs = voiced.frequencies
    print(f"\nPitch range: {freqs.min():.1f} - {freqs.max():.1f} Hz")
    print(f"Mean pitch: {freqs.mean():.1f} Hz")

    # Swara distribution
    swara_counts: dict[str, int] = {}
    for frame in voiced.frames:
        swara = freq_to_swara(frame.frequency_hz, reference_sa_hz=REFERENCE_SA_HZ)
        if swara:
            swara_counts[swara.swara_id] = swara_counts.get(swara.swara_id, 0) + 1

    if swara_counts:
        print(f"\nSwara distribution:")
        for name, count in sorted(swara_counts.items(), key=lambda x: -x[1]):
            pct = 100 * count / len(voiced.frames)
            bar = "#" * int(pct / 2)
            print(f"  {name:>6}: {count:>5} ({pct:5.1f}%) {bar}")


if __name__ == "__main__":
    main()
