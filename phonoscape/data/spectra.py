from typing import Literal
from dataclasses import dataclass

import numpy as np
from scipy.linalg import solve_toeplitz
from scipy.signal import freqz, lfilter, windows

from ..state import ActiveAnalysis, WindowState, Audio


@dataclass(frozen=True)
class CursorSpectra:
    frequency_hz: np.ndarray
    lpc_db: np.ndarray | None
    dft_db: np.ndarray | None
    avg_db: np.ndarray | None
    ceps_db: np.ndarray | None


def get_cursor_spectra(state: WindowState) -> CursorSpectra:
    assert state.selected_value.audio_traj is not None

    config = state.app_config
    audio = state.selected_value.audio_traj

    signal = get_analysis_frame(
        audio.signal, state.cursor_s, audio.sample_rate_hz, config.analysis_window_ms
    )
    signal = apply_pre_emphasis(signal, config.pre_emphasis)
    windowed_signal = windows.hann(signal.size, sym=True) * signal

    # For some reason, MVIEW actually uses f = linspace(0, sr/2, frame+1)
    frequency_hz = np.linspace(
        0.0, audio.sample_rate_hz / 2.0, config.fft_eval_points + 1
    )
    lpc_db = None
    dft_db = None
    avg_db = None
    ceps_db = None

    if config.active_analyses & ActiveAnalysis.LPC:
        lpc_db = lpc_spectrum_db(
            windowed_signal,
            audio.sample_rate_hz,
            config.lpc_order,
            config.fft_eval_points,
            config.spl_reference_μPa,
        )

    if config.active_analyses & ActiveAnalysis.DFT:
        dft_db = dft_spectrum_db(
            windowed_signal, config.fft_eval_points, config.spl_reference_μPa
        )

    if config.active_analyses & ActiveAnalysis.AVG:
        avg_db = avg_spectrum_db(
            signal,
            audio.sample_rate_hz,
            config.fft_eval_points,
            config.averaging_window_ms,
            config.overlap_ms,
            config.spl_reference_μPa,
        )

    if config.active_analyses & ActiveAnalysis.CEPS:
        ceps_db = ceps_spectrum_db(
            windowed_signal,
            audio.sample_rate_hz,
            config.fft_eval_points,
            config.spl_reference_μPa,
        )

    return CursorSpectra(
        frequency_hz=frequency_hz,
        lpc_db=lpc_db,
        dft_db=dft_db,
        avg_db=avg_db,
        ceps_db=ceps_db,
    )


def get_analysis_frame(
    signal: np.ndarray, cursor_s: float, sample_rate_hz: float, window_ms: float
) -> np.ndarray:
    ns = max(1, round(window_ms / 1000.0 * sample_rate_hz))
    cursor_idx = int(np.floor(cursor_s * sample_rate_hz))
    head = cursor_idx - round(ns / 2.0)

    if head < 0:
        head = 0

    tail = head + ns

    if tail > signal.size:
        tail = signal.size
        head = max(0, tail - ns)

    frame_signal = signal[head:tail]

    if frame_signal.size < ns:
        frame_signal = np.pad(frame_signal, (0, ns - frame_signal.size))

    return frame_signal


def apply_pre_emphasis(signal: np.ndarray, mu: float | None) -> np.ndarray:
    if signal.size == 0:
        return signal

    if mu is None:
        mu = get_adaptive_pre_emphasis(signal)

    if mu <= 0:
        return signal.copy()

    if mu > 1:
        raise ValueError(f"pre-emphasis coefficient error ({mu:g})")

    return lfilter([1.0, -mu], [1.0], signal)


def get_adaptive_pre_emphasis(signal: np.ndarray) -> float:
    r0 = float(np.dot(signal, signal))

    if r0 <= np.finfo(float).eps:
        return 0.0

    if signal.size < 2:
        return 0.0

    r1 = float(np.dot(signal[1:], signal[:-1]))
    return max(0.0, r1 / r0)


def lpc_autocorr(signal: np.ndarray, order: int) -> tuple[np.ndarray, float]:
    order = min(max(1, int(order)), signal.size - 1)

    if order < 1:
        return np.array([1.0]), np.finfo(float).eps

    autocorr = np.correlate(signal, signal, mode="full")[
        signal.size - 1 : signal.size + order
    ]

    if autocorr[0] <= np.finfo(float).eps:
        a = np.zeros(order + 1)
        a[0] = 1.0
        return a, np.finfo(float).eps

    coeffs = solve_toeplitz(
        (autocorr[:order], autocorr[:order]), -autocorr[1 : order + 1]
    )
    a = np.concatenate(([1.0], coeffs))
    error = float(autocorr[0] + np.dot(a[1:], autocorr[1 : order + 1]))
    gain = np.sqrt(max(error, np.finfo(float).eps))

    return a, gain


def lpc_spectrum_db(
    signal: np.ndarray,
    sample_rate_hz: float,
    order: int,
    fft_eval_points: int,
    reference_db: float,
) -> tuple[np.ndarray, np.ndarray]:
    a, gain = lpc_autocorr(signal, order)
    _, response = freqz(gain, a, worN=fft_eval_points + 1, fs=sample_rate_hz)

    response = np.abs(response)
    spectrum_db = 20.0 * np.log10(response / reference_db + np.finfo(float).eps)

    return spectrum_db


def dft_spectrum_db(
    signal: np.ndarray, fft_eval_points: int, reference_db: float
) -> np.ndarray:
    spectrum = np.abs(np.fft.fft(signal, fft_eval_points * 2))
    spectrum = spectrum[: fft_eval_points + 1]
    return 20.0 * np.log10(spectrum / reference_db + np.finfo(float).eps)


def avg_spectrum_db(
    signal: np.ndarray,
    sample_rate_hz: float,
    fft_eval_points: int,
    averaging_window_ms: float,
    overlap_ms: float,
    reference_db: float,
) -> np.ndarray:
    avg_window_samples = max(
        1, int(np.floor(averaging_window_ms * sample_rate_hz / 1000.0))
    )
    avg_window_samples = avg_window_samples + 1 - avg_window_samples % 2
    shift_samples = max(1, int(np.floor(overlap_ms * sample_rate_hz / 1000.0)))
    avg_fft_points = 2 ** int(np.ceil(np.log2(avg_window_samples)))
    n_frames = round(signal.size / shift_samples) + 1

    window = windows.hamming(avg_window_samples, sym=True)
    padded_signal = np.concatenate(
        (np.zeros(avg_window_samples), signal, np.zeros(avg_window_samples))
    )
    start_sample = int(np.ceil(avg_window_samples / 2.0))

    spectra = np.zeros((avg_fft_points + 1, n_frames))

    for frame_idx in range(n_frames):
        frame = padded_signal[start_sample : start_sample + avg_window_samples]
        frame_spectrum = np.abs(np.fft.fft(window * frame, avg_fft_points * 2))
        spectra[:, frame_idx] = frame_spectrum[: avg_fft_points + 1]
        start_sample += shift_samples

    averaged_spectrum = spectra.mean(axis=1)

    source_frequency_hz = np.linspace(0.0, sample_rate_hz / 2.0, avg_fft_points + 1)
    target_frequency_hz = np.linspace(0.0, sample_rate_hz / 2.0, fft_eval_points + 1)
    interpolated = np.interp(
        target_frequency_hz, source_frequency_hz, averaged_spectrum
    )

    return 20.0 * np.log10(interpolated / reference_db + np.finfo(float).eps)


def ceps_spectrum_db(
    signal: np.ndarray,
    sample_rate_hz: float,
    fft_eval_points: int,
    reference_db: float,
) -> np.ndarray:
    spectrum = np.abs(np.fft.fft(signal, fft_eval_points * 2))
    cepstrum = np.real(
        np.fft.ifft(np.log(spectrum + np.finfo(float).eps), fft_eval_points * 2)
    )

    search = np.abs(cepstrum[10:fft_eval_points])

    if search.size == 0 or np.mean(search) <= np.finfo(float).eps:
        n_coefficients = round(25 * sample_rate_hz / 10000.0)
    else:
        peak_offset = int(np.argmax(search))
        peak_idx = peak_offset + 10
        peak_value = search[peak_offset]

        if (
            peak_value / np.mean(search) > 10.0
            and round(sample_rate_hz / peak_idx) < 200
        ):
            n_coefficients = round(peak_idx / 3.0)
        else:
            n_coefficients = round(25 * sample_rate_hz / 10000.0)

    n_coefficients = int(np.clip(n_coefficients, 1, fft_eval_points - 1))
    cepstrum[n_coefficients : fft_eval_points * 2 - n_coefficients] = 0.0

    smoothed_spectrum = np.exp(np.abs(np.fft.fft(cepstrum))[: fft_eval_points + 1])

    return 20.0 * np.log10(smoothed_spectrum / reference_db + np.finfo(float).eps)


@dataclass(frozen=True)
class CogMeasure:
    l1: float
    skew: float
    kurt: float


def get_cog(
    traj: Audio,
    time_s: float,
    alg: Literal["AVG", "WIN"],
    spec: Literal["MAG", "POW"],
    preemp: float | None,
    cutoff_hz: float,
    window_ms: float,
    fft_eval_points: int,
    avg_window_ms: float,
    overlap_ms: float,
) -> CogMeasure:
    signal = get_analysis_frame(traj.signal, time_s, traj.sample_rate_hz, window_ms)
    signal = apply_pre_emphasis(signal, preemp)
    algorithm = alg.upper()
    use_power = spec.upper() == "POW"
    if spec.upper() not in {"MAG", "POW"}:
        raise ValueError(f"unrecognized spectrum type ({spec})")
    if algorithm == "AVG":
        spectrum = _cog_avg_spectrum(
            signal,
            traj.sample_rate_hz,
            fft_eval_points,
            avg_window_ms,
            overlap_ms,
            use_power,
        )
    elif algorithm == "WIN":
        spectrum = _cog_win_spectrum(signal, fft_eval_points, use_power)
    else:
        raise ValueError(f"unrecognized COG algorithm: {alg}")
    return _cog_moments(spectrum, traj.sample_rate_hz, fft_eval_points, cutoff_hz)


def _cog_avg_spectrum(
    signal: np.ndarray,
    sample_rate_hz: float,
    fft_eval_points: int,
    avg_window_ms: float,
    overlap_ms: float,
    use_power: bool,
) -> np.ndarray:
    avg_window_samples = max(1, int(np.floor(avg_window_ms * sample_rate_hz / 1000.0)))
    shift_samples = max(1, int(np.floor(overlap_ms * sample_rate_hz / 1000.0)))
    n_frames = round(signal.size / shift_samples) + 1

    window = np.hamming(avg_window_samples)
    padded_signal = np.concatenate(
        (np.zeros(avg_window_samples), signal, np.zeros(avg_window_samples))
    )
    start_sample = int(np.ceil(avg_window_samples / 2.0)) - 1

    spectra = np.zeros((fft_eval_points, n_frames), dtype=np.float64)

    for frame_idx in range(n_frames):
        chunk = padded_signal[start_sample : start_sample + avg_window_samples]
        fft_vals = np.fft.fft(window * chunk, n=fft_eval_points * 2)
        spectra[:, frame_idx] = _cog_fft_bins(fft_vals, fft_eval_points, use_power)
        start_sample += shift_samples

    return spectra.mean(axis=1)


def _cog_win_spectrum(
    signal: np.ndarray, fft_eval_points: int, use_power: bool
) -> np.ndarray:
    window = np.hanning(signal.size)
    fft_vals = np.fft.fft(window * signal, n=fft_eval_points * 2)
    return _cog_fft_bins(fft_vals, fft_eval_points, use_power)


def _cog_fft_bins(
    fft_vals: np.ndarray, fft_eval_points: int, use_power: bool
) -> np.ndarray:
    one_sided = fft_vals[:fft_eval_points]

    if use_power:
        return np.real(one_sided) ** 2 + np.imag(one_sided) ** 2

    return np.abs(one_sided)


def _cog_moments(
    spectrum: np.ndarray,
    sample_rate_hz: float,
    fft_eval_points: int,
    cutoff_hz: float,
) -> CogMeasure:
    upper_bin = round(cutoff_hz * fft_eval_points * 2.0 / sample_rate_hz)
    upper_bin = min(fft_eval_points, upper_bin)

    if upper_bin <= 1:
        return CogMeasure(l1=np.nan, skew=np.nan, kurt=np.nan)

    spectrum = spectrum[:upper_bin]
    total = float(np.sum(spectrum))

    if total <= 0.0 or not np.isfinite(total):
        return CogMeasure(l1=np.nan, skew=np.nan, kurt=np.nan)

    normalized = spectrum / total
    normalized = normalized[1:]

    frequencies_hz = (
        np.linspace(1.0, float(upper_bin), upper_bin - 1)
        * sample_rate_hz
        / (fft_eval_points * 2.0)
    )

    l1 = float(np.sum(frequencies_hz * normalized))
    centered = frequencies_hz - l1

    l2 = float(np.sum(centered**2 * normalized))
    l3 = float(np.sum(centered**3 * normalized))
    l4 = float(np.sum(centered**4 * normalized))

    if l2 <= 0.0 or not np.isfinite(l2):
        return CogMeasure(l1=l1, skew=np.nan, kurt=np.nan)

    skew = l3 / (l2**1.5)
    kurt = l4 / (l2**2) - 3.0

    return CogMeasure(l1=l1, skew=float(skew), kurt=float(kurt))
