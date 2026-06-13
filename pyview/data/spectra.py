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
    spectrum = spectrum[:fft_eval_points + 1]
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
