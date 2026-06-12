from dataclasses import dataclass

import numpy as np
from scipy.linalg import solve_toeplitz
from scipy.signal import freqz, lfilter, windows

from ..state import ActiveAnalysis, WindowState


@dataclass(frozen=True)
class CursorSpectra:
    frequency_hz: np.ndarray
    lpc_db: np.ndarray | None
    dft_db: np.ndarray | None


def get_cursor_spectra(state: WindowState) -> CursorSpectra:
    assert state.selected_value.audio_traj is not None

    config = state.app_config
    audio = state.selected_value.audio_traj
    sample_rate_hz = audio.sample_rate_hz
    fft_eval_points = max(1, int(config.fft_eval_points))
    reference_db = max(float(config.spl_reference_db), 1.0)

    signal = get_analysis_frame(
        audio.signal, state.cursor_s, sample_rate_hz, config.analysis_window_ms
    )
    signal = apply_pre_emphasis(signal, config.pre_emphasis)
    signal = windows.hann(signal.size, sym=True) * signal

    frequency_hz = np.linspace(0.0, sample_rate_hz / 2.0, fft_eval_points + 1)[1:]
    lpc_db = None
    dft_db = None

    if config.active_analyses & ActiveAnalysis.LPC:
        _, lpc_db = lpc_spectrum_db(
            signal, sample_rate_hz, config.lpc_order, fft_eval_points, reference_db
        )

    if config.active_analyses & ActiveAnalysis.DFT:
        dft_db = dft_spectrum_db(signal, fft_eval_points, reference_db)

    return CursorSpectra(frequency_hz=frequency_hz, lpc_db=lpc_db, dft_db=dft_db)


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


def apply_pre_emphasis(signal: np.ndarray, mu: float) -> np.ndarray:
    if signal.size == 0:
        return signal

    if mu < 0:
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
    frequency_hz, response = freqz(gain, a, worN=fft_eval_points + 1, fs=sample_rate_hz)

    frequency_hz = frequency_hz[1:]
    response = np.abs(response[1:])
    spectrum_db = 20.0 * np.log10(response / reference_db + np.finfo(float).eps)

    return frequency_hz, spectrum_db


def dft_spectrum_db(
    signal: np.ndarray, fft_eval_points: int, reference_db: float
) -> np.ndarray:
    spectrum = np.abs(np.fft.fft(signal, fft_eval_points * 2))
    spectrum = spectrum[1 : fft_eval_points + 1]
    return 20.0 * np.log10(spectrum / reference_db + np.finfo(float).eps)
