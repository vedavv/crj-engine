"""Tonic (Sa) detection — pitch-class histogram with Sa-Pa relationship validation.

Algorithm:
  1. Run pYIN on the audio to get an F0 contour.
  2. Filter to confidently-voiced frames (typical drone+vocal recordings have ~70%
     voiced content).
  3. Fold every F0 into a single octave (cents-mod-1200) weighted by frame duration.
  4. Smooth the resulting 1200-bin histogram with a Gaussian (sigma=10 cents) to
     suppress spurious micro-peaks while preserving microtonal structure.
  5. Pick the top peaks; for each candidate pitch-class, find the strongest
     absolute Hz peak in the Carnatic/Hindustani vocal Sa range (80-400 Hz) so
     we resolve the right octave.
  6. Boost confidence when a secondary peak appears at +700 cents (Sa-Pa) since
     a present Pa is the strongest single indicator that the candidate really
     is Sa rather than another sustained note.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from crj_engine.pitch.detector import detect_pitch_pyin

# Vocal Sa typically sits between A2 (110 Hz, low male) and A4 (440 Hz, high female).
_SA_HZ_MIN = 80.0
_SA_HZ_MAX = 440.0

# Reference frequency used for cents-folding. Anything well below Sa range works.
_FOLD_REF_HZ = 55.0  # A1


@dataclass
class TonicCandidate:
    sa_hz: float
    western_label: str
    confidence: float
    has_perfect_fifth: bool


@dataclass
class TonicResult:
    suggested_sa_hz: float
    western_label: str
    confidence: float
    candidates: list[TonicCandidate]
    voiced_frame_count: int


def _hz_to_western(hz: float) -> str:
    """Nearest Western note name + octave (e.g. 'C4', 'D#4'). Latin letters only."""
    if hz <= 0:
        return "?"
    midi = 69 + 12 * np.log2(hz / 440.0)
    midi_round = int(round(midi))
    notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    name = notes[midi_round % 12]
    octave = (midi_round // 12) - 1
    return f"{name}{octave}"


def _gaussian_smooth(arr: np.ndarray, sigma: float = 10.0) -> np.ndarray:
    """1D circular Gaussian smoothing (avoids scipy dep)."""
    radius = int(sigma * 4)
    if radius < 1:
        return arr.astype(float)
    kernel_x = np.arange(-radius, radius + 1)
    kernel = np.exp(-(kernel_x ** 2) / (2 * sigma * sigma))
    kernel /= kernel.sum()
    # Wrap-around convolution (the histogram is circular: 1200 cents)
    padded = np.concatenate([arr[-radius:], arr, arr[:radius]])
    smoothed = np.convolve(padded, kernel, mode="valid")
    return smoothed


def _absolute_sa_hz(
    target_pitch_class: int, voiced_freqs: np.ndarray
) -> float | None:
    """Resolve the absolute Sa frequency from a pitch-class candidate.

    Picks all voiced frames whose pitch class is within 30 cents of the target,
    restricted to the vocal Sa range, then groups them by octave and returns
    the median of the most-populated octave bin. The grouping protects against
    pYIN's sub-octave autocorrelation errors — a few frames in the wrong
    octave shouldn't drag the answer down by 1200 cents.
    """
    if len(voiced_freqs) == 0:
        return None

    cents_in_octave = (1200 * np.log2(voiced_freqs / _FOLD_REF_HZ)) % 1200
    distances = np.minimum(
        np.abs(cents_in_octave - target_pitch_class),
        1200 - np.abs(cents_in_octave - target_pitch_class),
    )
    in_class = distances < 30
    in_range = (voiced_freqs >= _SA_HZ_MIN) & (voiced_freqs <= _SA_HZ_MAX)
    matches = voiced_freqs[in_class & in_range]
    if len(matches) == 0:
        return None

    # Group by octave (each octave = 1.0 in log2 space). Pick the bin with the
    # most votes; if there's a tie, prefer the higher octave (pYIN sub-octave
    # errors are more common than super-octave errors).
    log_freqs = np.log2(matches)
    octave_bins = np.floor(log_freqs).astype(int)
    unique_octaves, counts = np.unique(octave_bins, return_counts=True)
    max_count = counts.max()
    winning_octaves = unique_octaves[counts == max_count]
    best_octave = int(winning_octaves.max())  # tiebreak toward higher octave
    in_best_octave = octave_bins == best_octave
    return float(np.median(matches[in_best_octave]))


def _voiced_freqs_from_audio(
    audio: np.ndarray, sr: int, fmin: float, min_confidence: float
) -> np.ndarray:
    contour = detect_pitch_pyin(
        audio, sr=sr, hop_ms=10.0, min_confidence=min_confidence, fmin=fmin
    )
    return np.array(
        [
            f.frequency_hz
            for f in contour.frames
            if f.confidence >= min_confidence and f.frequency_hz > 0
        ],
        dtype=np.float64,
    )


def _spectrum_band_energy(
    spectrum: np.ndarray, freqs: np.ndarray, target_hz: float, bw_cents: float = 50.0
) -> float:
    low = target_hz * (2 ** (-bw_cents / 1200))
    high = target_hz * (2 ** (bw_cents / 1200))
    mask = (freqs >= low) & (freqs <= high)
    return float(spectrum[mask].sum())


def _audio_spectrum(
    audio: np.ndarray, sr: int
) -> tuple[np.ndarray, np.ndarray] | None:
    n = min(len(audio), int(sr * 4))
    if n < 1024:
        return None
    clip = audio[:n].astype(np.float64) * np.hanning(n)
    spectrum = np.abs(np.fft.rfft(clip))
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)
    return spectrum, freqs


def _has_perfect_fifth_spectral(
    audio: np.ndarray, sr: int, sa_hz: float, *, min_ratio: float = 0.3
) -> bool:
    """Detect whether the audio contains a sustained Pa partner of `sa_hz`.

    pYIN only emits one F0 per frame, so when both Sa and Pa are sounding
    together (tanpura, two-voice drone) the histogram only sees whichever
    one pYIN tracked. The FFT shows both simultaneously, so we ask: does the
    band around Pa contain at least `min_ratio` of the Sa band's energy?
    """
    spec = _audio_spectrum(audio, sr)
    if spec is None:
        return False
    spectrum, freqs = spec
    pa_hz = sa_hz * (2 ** (700 / 1200.0))
    sa_e = _spectrum_band_energy(spectrum, freqs, sa_hz)
    pa_e = _spectrum_band_energy(spectrum, freqs, pa_hz)
    if sa_e <= 0:
        return False
    return pa_e >= sa_e * min_ratio


def _spectrum_verified_sa(
    audio: np.ndarray, sr: int, candidate_sa_hz: float
) -> float:
    """Verify the chosen octave against the audio's actual FFT.

    pYIN's autocorrelation can latch onto T/2 (sub-octave error) when the
    signal has a strong 2nd harmonic — common in tanpura drones, vocals
    with prominent overtones, and any synthesized harmonic stack. We compare
    spectral energy at the candidate vs. at 2x candidate. If 2x has clearly
    more energy AND fits in the vocal Sa range, the candidate was a sub-
    octave error and we bump it up.
    """
    if candidate_sa_hz * 2 > _SA_HZ_MAX:
        return candidate_sa_hz

    # Use up to ~4s of audio for a stable spectrum; longer windows blur
    # short-term variation but improve frequency resolution.
    n = min(len(audio), int(sr * 4))
    if n < 1024:
        return candidate_sa_hz

    clip = audio[:n].astype(np.float64) * np.hanning(n)
    spectrum = np.abs(np.fft.rfft(clip))
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)

    def band_energy(target_hz: float, bw_cents: float = 50.0) -> float:
        low = target_hz * (2 ** (-bw_cents / 1200))
        high = target_hz * (2 ** (bw_cents / 1200))
        mask = (freqs >= low) & (freqs <= high)
        return float(spectrum[mask].sum())

    e_low = band_energy(candidate_sa_hz)
    e_high = band_energy(candidate_sa_hz * 2)

    # Bump up when the higher octave dominates by a clear margin. Real
    # fundamentals are usually >= 2nd harmonic, so a ratio > 1.5 is a strong
    # signal that pYIN gave us the sub-octave.
    if e_high > e_low * 1.5:
        return candidate_sa_hz * 2.0
    return candidate_sa_hz


def detect_tonic(
    audio: np.ndarray,
    sr: int = 16000,
    *,
    min_confidence: float = 0.5,
    top_n: int = 3,
) -> TonicResult:
    """Detect the most likely Sa frequency for an audio clip.

    Args:
        audio: Mono audio samples (float32 numpy array).
        sr: Sample rate.
        min_confidence: pYIN confidence threshold for voiced frames.
        top_n: Number of candidates to return.

    Returns:
        TonicResult with suggested_sa_hz, top candidates, and a confidence score
        in [0, 1]. Confidence below ~0.3 means we couldn't find a clear tonic.
    """
    # Two-pass pYIN: prefer fmin=180 to suppress autocorrelation sub-octave
    # errors on harmonic-rich vocal/tanpura signals (most Sas land in
    # F#3-G#4). Fall back to a wider range only if the high-fmin pass yields
    # too few voiced frames (genuine low-male Sa below F#3).
    voiced = _voiced_freqs_from_audio(audio, sr, fmin=180.0, min_confidence=min_confidence)
    if len(voiced) < 50:
        voiced = _voiced_freqs_from_audio(audio, sr, fmin=80.0, min_confidence=min_confidence)

    if len(voiced) < 50:
        return TonicResult(
            suggested_sa_hz=261.63,
            western_label="C4",
            confidence=0.0,
            candidates=[],
            voiced_frame_count=int(len(voiced)),
        )

    # Build pitch-class histogram (1200 1-cent bins)
    cents_in_octave = (1200 * np.log2(voiced / _FOLD_REF_HZ)) % 1200
    hist, _ = np.histogram(cents_in_octave, bins=1200, range=(0, 1200))
    hist_smooth = _gaussian_smooth(hist.astype(float), sigma=10.0)

    mean_h = float(hist_smooth.mean()) or 1.0

    # Find local maxima (compare each bin against ±20-cent neighborhood)
    radius = 20
    n_bins = len(hist_smooth)
    is_peak = np.zeros(n_bins, dtype=bool)
    for i in range(n_bins):
        start = (i - radius) % n_bins
        end = (i + radius + 1) % n_bins
        if start < end:
            window = hist_smooth[start:end]
        else:
            window = np.concatenate([hist_smooth[start:], hist_smooth[:end]])
        if hist_smooth[i] >= window.max() and hist_smooth[i] > mean_h:
            is_peak[i] = True

    peak_indices = np.where(is_peak)[0]
    if len(peak_indices) == 0:
        return TonicResult(
            suggested_sa_hz=261.63,
            western_label="C4",
            confidence=0.0,
            candidates=[],
            voiced_frame_count=int(len(voiced)),
        )

    # Sort peaks by strength
    peak_strengths = hist_smooth[peak_indices]
    sorted_idx = np.argsort(peak_strengths)[::-1]
    top_peaks = peak_indices[sorted_idx][: top_n * 2]  # over-collect, filter later

    candidates: list[TonicCandidate] = []
    for peak_pc in top_peaks:
        sa_hz = _absolute_sa_hz(int(peak_pc), voiced)
        if sa_hz is None:
            continue

        # Disambiguate sub-octave errors using the audio spectrum
        sa_hz = _spectrum_verified_sa(audio, sr, sa_hz)

        # Base confidence from peak prominence
        prominence = hist_smooth[peak_pc] / mean_h
        confidence = min(1.0, prominence / 6.0)

        # Sa-Pa boost: spectral check is robust both for pYIN-tracked Pa
        # (histogram peak at +700 cents) and for cases where pYIN locked onto
        # Sa but Pa is sounding simultaneously in the audio.
        pa_pc = (peak_pc + 700) % 1200
        pa_strength = hist_smooth[pa_pc] / mean_h
        has_fifth = (
            pa_strength > 1.6 or _has_perfect_fifth_spectral(audio, sr, sa_hz)
        )
        if has_fifth:
            confidence = min(1.0, confidence * 1.3)

        candidates.append(
            TonicCandidate(
                sa_hz=round(sa_hz, 2),
                western_label=_hz_to_western(sa_hz),
                confidence=round(confidence, 3),
                has_perfect_fifth=has_fifth,
            )
        )
        if len(candidates) >= top_n:
            break

    if not candidates:
        return TonicResult(
            suggested_sa_hz=261.63,
            western_label="C4",
            confidence=0.0,
            candidates=[],
            voiced_frame_count=int(len(voiced)),
        )

    best = candidates[0]
    return TonicResult(
        suggested_sa_hz=best.sa_hz,
        western_label=best.western_label,
        confidence=best.confidence,
        candidates=candidates,
        voiced_frame_count=int(len(voiced)),
    )
