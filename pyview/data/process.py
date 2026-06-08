from typing import cast

import numpy as np
from scipy.signal import ShortTimeFFT, windows, filtfilt, lfilter

from ..state import TrajDisplay, DatasetVariable, Trajectory, Audio


def get_spect(traj: Trajectory):
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
    extent = [0, traj.n_samples / traj.sample_rate_hz, 0, traj.sample_rate_hz / 2]
    return extent, S_db


def get_rms(traj: Trajectory):
    window = round(20 * traj.sample_rate_hz / 1000)  # 20 msec filter window
    b = np.ones(window) / window  # rectwin(window) ./ window
    rms: np.ndarray = np.sqrt(np.abs(filtfilt(b, [1], traj.data**2)))
    return rms


def get_zc(traj: Trajectory):
    wl = round(20 * traj.sample_rate_hz / 1000)  # 20 msec filter window
    wl2 = int(np.ceil(wl / 2))
    s = np.concatenate([np.zeros(wl2), traj.data, np.zeros(wl2)])
    zc = cast(
        np.ndarray,
        lfilter(np.ones(wl), [1], np.concatenate([[0], np.abs(np.diff(s >= 0))])),
    )
    zc: np.ndarray = zc[wl2 * 2 :]
    return zc


def analyze_audio(traj: Trajectory):
    t = np.arange(traj.n_samples) / traj.sample_rate_hz
    extent, S_db = get_spect(traj)
    rms = get_rms(traj)
    zc = get_zc(traj)
    return Audio(
        name=traj.name,
        sample_rate_hz=traj.sample_rate_hz,
        n_samples=traj.n_samples,
        signal=traj.data,
        spect=(extent, S_db),
        rms=rms,
        rms_db=20 * np.log10(rms + np.finfo(float).eps),
        zc=zc,
        f0_hz=np.array([]),  # TODO: implement
        l1=np.array([]),  # TODO: implement
        skew=np.array([]),  # TODO: implement
        kurt=np.array([]),  # TODO: implement
        formants=[],  # TODO: implement
    )


def get_plotting_data(var: DatasetVariable, spec: TrajDisplay, dimensions: int):
    # Fast path: reuse precomputed audio data
    if var.audio_traj and spec.traj_name == var.audio_traj.name:
        traj = var.audio_traj
        t = np.arange(traj.n_samples) / traj.sample_rate_hz
        match spec.content:
            case "SIGNAL":
                return t, traj.signal
            case "SPECT":
                return traj.spect
            case "RMS":
                return t, traj.rms
            case "ZC":
                return t, traj.zc

    traj = var.trajectories[spec.traj_name]
    t = np.arange(traj.n_samples) / traj.sample_rate_hz
    match spec.content:
        case "SPECT":
            return get_spect(traj)
        case "SIGNAL":
            return t, traj.data
        case "VEL":
            vs: np.ndarray = np.gradient(traj.data) * traj.sample_rate_hz
            return t, vs
        case "ABSVEL":
            vs: np.ndarray = np.abs(np.gradient(traj.data) * traj.sample_rate_hz)
            return t, vs
        case "RMS":
            return t, get_rms(traj)
        case "ZC":
            return t, get_zc(traj)
        case "movement" | "velocity" | "acceleration":
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
        case x:
            raise ValueError(f"Unexpected content type for temporal display: {x}")
