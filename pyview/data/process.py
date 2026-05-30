from typing import cast

import numpy as np
from scipy.signal import ShortTimeFFT, windows, filtfilt, lfilter

from ..state import TrajDisplay, Trajectory


def get_plotting_data(traj: Trajectory, spec: TrajDisplay):
    t = np.arange(traj.n_samples) / traj.sample_rate_hz
    if spec.content == "SPECT":
        window_ms = 25
        overlap = 0.75
        nperseg = round(traj.sample_rate_hz * window_ms / 1000)
        hop = max(1, round(nperseg * (1.0 - overlap)))
        win = windows.hann(nperseg, sym=False)
        stft = ShortTimeFFT(
            win=win,
            hop=hop,
            fs=traj.sample_rate_hz,
            mfft=1024,
            scale_to="magnitude",
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
        zc = cast(np.ndarray, lfilter(
            np.ones(wl),  # rectwin(wl)
            [1],
            np.concatenate([[0], np.abs(np.diff(s >= 0))]),
        ))
        zc: np.ndarray = zc[wl2 * 2 :]
        return t, zc
    elif spec.content in ("movement", "velocity", "acceleration"):
        cols = [{"x": 0, "y": 1, "z": 2}[comp] for comp in spec.components]
        ps = traj.data[:, cols]
        if spec.content == "movement":
            return t, ps
        vs = np.gradient(ps, axis=0) * traj.sample_rate_hz
        if spec.content == "velocity":
            if vs.shape[1] > 1:
                speed: np.ndarray = np.linalg.norm(vs, axis=1)
            else:
                # Preserve sign for 1D
                # TODO: currently this way for mview compatibility, but I think
                # "velocity" and "speed" should be separate content types
                # Otherwise there's this inconsistency between 1D and multi-D
                speed = vs[:, 0]
            return t, speed
        accs = np.gradient(vs, axis=0) * traj.sample_rate_hz
        if accs.shape[1] > 1:
            accel: np.ndarray = np.linalg.norm(accs, axis=1)
        else:
            accel = accs[:, 0]
        return t, accel
    else:
        raise ValueError(
            f"Unexpected content type for temporal display: {spec.content}"
        )
