from typing import cast
from dataclasses import dataclass

import numpy as np
from scipy.signal import ShortTimeFFT, windows, filtfilt, lfilter

from ..state import TrajDisplay, Trajectory


def get_plotting_data(traj: Trajectory, spec: TrajDisplay, dimensions: int):
    t = np.arange(traj.n_samples) / traj.sample_rate_hz
    if spec.content == "SPECT":
        window_ms = 25
        overlap = 0.75
        nperseg = round(traj.sample_rate_hz * window_ms / 1000)
        hop = max(1, round(nperseg * (1.0 - overlap)))
        win = windows.hann(nperseg, sym=False)
        stft = ShortTimeFFT(
            win=win, hop=hop, fs=traj.sample_rate_hz, mfft=1024, scale_to="magnitude"
        )
        S = stft.spectrogram(traj.data)
        S_db = 20 * np.log10(S + np.finfo(float).eps)
        extent = [0, t[-1], 0, traj.sample_rate_hz / 2]
        return extent, S_db
    elif spec.content == "SIGNAL":
        return t, traj.data
    elif spec.content == "VEL":
        vs: np.ndarray = np.gradient(traj.data) * traj.sample_rate_hz
        return t, vs
    elif spec.content == "ABSVEL":
        vs: np.ndarray = np.abs(np.gradient(traj.data) * traj.sample_rate_hz)
        return t, vs
    elif spec.content == "RMS":
        window = round(20 * traj.sample_rate_hz / 1000)  # 20 msec filter window
        b = np.ones(window) / window  # rectwin(window) ./ window
        rms: np.ndarray = np.sqrt(np.abs(filtfilt(b, [1], traj.data**2)))
        return t, rms
    elif spec.content == "ZC":
        wl = round(20 * traj.sample_rate_hz / 1000)  # 20 msec filter window
        wl2 = int(np.ceil(wl / 2))
        s = np.concatenate([np.zeros(wl2), traj.data, np.zeros(wl2)])
        zc = cast(
            np.ndarray,
            lfilter(np.ones(wl), [1], np.concatenate([[0], np.abs(np.diff(s >= 0))])),
        )
        zc: np.ndarray = zc[wl2 * 2 :]
        return t, zc
    elif spec.content in ("movement", "velocity", "acceleration"):
        cols = [{"x": 0, "y": 1, "z": 2}[comp] for comp in spec.components]
        ps = traj.data[:, cols]
        if spec.content == "movement":
            return t, ps
        vs = np.gradient(ps, axis=0) * traj.sample_rate_hz
        if spec.content == "velocity":
            if vs.shape[1] == dimensions:
                # Collapse if viewing all components
                # TODO: currently this way for mview compatibility, but I think
                # "velocity" and "speed" should be separate content types
                # Otherwise there's this inconsistency
                return t, np.array([np.linalg.norm(vs, axis=1)]).T
            return t, vs
        accs = np.gradient(vs, axis=0) * traj.sample_rate_hz
        if accs.shape[1] == dimensions:
            return t, np.array([np.linalg.norm(accs, axis=1)]).T
        return t, accs
    else:
        raise ValueError(
            f"Unexpected content type for temporal display: {spec.content}"
        )


@dataclass
class LocalMeasures:
    zero_crossings: int
    rms: float
    rms_db: float
    f0_hz: float
    L1: float
    skew: float
    kurt: float
    formants: list[tuple[float, float]]  # (frequency, bandwidth)


def get_local_measures(traj: Trajectory, cursor_s: float, window_ms: float):
    section_samples = round(traj.sample_rate_hz * window_ms / 1000)
    center_sample = round(cursor_s * traj.sample_rate_hz)
    start_sample = max(0, center_sample - section_samples // 2)
    end_sample = min(traj.n_samples, center_sample + section_samples // 2)
    section = traj.data[start_sample:end_sample]
    zero_crossings = np.sum(np.abs(np.diff(section >= 0)))
    rms = np.sqrt(np.mean(section**2))
    rms_db = 20 * np.log10(rms + np.finfo(float).eps)
    f0_hz = 0.0  # TODO: pitch detection
    L1 = 0.0  # TODO: spectral center of gravity
    skew = 0.0  # TODO: spectral skewness
    kurt = 0.0  # TODO: spectral kurtosis
    formants = []  # TODO: formant estimation
    return LocalMeasures(
        zero_crossings=zero_crossings,
        rms=rms,
        rms_db=rms_db,
        f0_hz=f0_hz,
        L1=L1,
        skew=skew,
        kurt=kurt,
        formants=formants,
    )
