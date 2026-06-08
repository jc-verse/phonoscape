from typing import cast

from amfm_decompy import basic_tools
from amfm_decompy import pYAAPT
import numpy as np
from numpy.typing import NDArray
from scipy.signal import ShortTimeFFT, windows, filtfilt, lfilter
from scipy.ndimage import gaussian_filter1d


from ..state import TrajDisplay, DatasetVariable, Trajectory, Audio, F0Track


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
    extent: list[float] = [
        0,
        traj.n_samples / traj.sample_rate_hz,
        0,
        traj.sample_rate_hz / 2,
    ]
    return extent, S_db


def get_rms(traj: Trajectory):
    window = round(20 * traj.sample_rate_hz / 1000)  # 20 msec filter window
    b = np.ones(window) / window  # rectwin(window) ./ window
    rms: NDArray[np.float64] = np.sqrt(np.abs(filtfilt(b, [1], traj.data**2)))
    return rms


def get_zc(traj: Trajectory):
    wl = round(20 * traj.sample_rate_hz / 1000)  # 20 msec filter window
    wl2 = int(np.ceil(wl / 2))
    s = np.concatenate([np.zeros(wl2), traj.data, np.zeros(wl2)])
    zc = cast(
        NDArray[np.float64],
        lfilter(np.ones(wl), [1], np.concatenate([[0], np.abs(np.diff(s >= 0))])),
    )
    zc = zc[wl2 * 2 :]
    return zc


def _interp_zeros(f0: NDArray[np.float64]) -> NDArray[np.float64]:
    f0 = f0.copy()
    f0[f0 == 0] = np.nan

    good = np.isfinite(f0)
    if not np.any(good):
        return np.zeros_like(f0)

    x = np.arange(len(f0))
    f0[~good] = np.interp(x[~good], x[good], f0[good])
    return f0


def get_f0(
    traj: Trajectory,
    frame_ms: float = 35.0,
    hop_ms: float = 10.0,
    fmin_hz: float = 60.0,
    fmax_hz: float = 400.0,
) -> F0Track:
    signal = basic_tools.SignalObj(np.ravel(traj.data), traj.sample_rate_hz)

    pitch = pYAAPT.yaapt(
        signal,
        frame_length=frame_ms,
        frame_lengtht=frame_ms,
        frame_space=hop_ms,
        f0_min=fmin_hz,
        f0_max=fmax_hz,
    )

    # pYAAPT's pitch.values is the final pitch track in Hz. In YAAPT convention,
    # unvoiced frames are represented as 0.
    raw_hz = np.asarray(pitch.values, dtype=np.float64)

    duration_s = traj.n_samples / traj.sample_rate_hz
    f0_sample_rate_hz = 0.0 if duration_s == 0 else len(raw_hz) / duration_s

    return F0Track(
        sample_rate_hz=f0_sample_rate_hz,
        raw_hz=raw_hz,
        interp_hz=_interp_zeros(raw_hz),
    )


def analyze_audio(traj: Trajectory):
    extent, S_db = get_spect(traj)
    rms = get_rms(traj)
    zc = get_zc(traj)
    f0 = get_f0(traj)
    return Audio(
        name=traj.name,
        sample_rate_hz=traj.sample_rate_hz,
        n_samples=traj.n_samples,
        signal=traj.data,
        spect=(extent, S_db),
        rms=rms,
        rms_db=20 * np.log10(rms + np.finfo(float).eps),
        zc=zc,
        f0=f0,
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
            case "F0":
                return (
                    np.arange(len(traj.f0.raw_hz)) / traj.f0.sample_rate_hz,
                    traj.f0.raw_hz,
                )

    traj = var.trajectories[spec.traj_name]
    t = np.arange(traj.n_samples) / traj.sample_rate_hz
    match spec.content:
        case "SPECT":
            return get_spect(traj)
        case "SIGNAL":
            return t, traj.data
        case "VEL":
            vs: NDArray[np.float64] = np.gradient(traj.data) * traj.sample_rate_hz
            return t, vs
        case "ABSVEL":
            vs: NDArray[np.float64] = np.abs(
                np.gradient(traj.data) * traj.sample_rate_hz
            )
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
