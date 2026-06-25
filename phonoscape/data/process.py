from typing import cast, overload

from amfm_decompy import basic_tools
from amfm_decompy import pYAAPT
import numpy as np
from numpy.typing import NDArray
from scipy.signal import ShortTimeFFT, windows, filtfilt, lfilter
from scipy.interpolate import splprep, splev


from ..state import TrajDisplay, DatasetVariable, Trajectory, Audio, F0Track, AppConfig


def get_spect(traj: Trajectory, frame: int, win_ms: float, hop_ms: float, mult: int):
    # MVIEW temporal spectrogram uses first-difference pre-emphasis,
    # not the configurable PREEMP value.
    # TODO: I think we should apply pre_emphasis here
    signal = np.diff(traj.data, prepend=traj.data[0])

    nperseg = round(traj.sample_rate_hz * win_ms / 1000)
    nperseg = max(1, nperseg * mult)
    # MVIEW makes the resulting window length even.
    nperseg += nperseg % 2

    # In MVIEW, OLAP is effectively the frame shift in milliseconds.
    # MVIEW applies MULT to the spectrogram window size, not to hop/OLAP.
    hop_samples = round(traj.sample_rate_hz * hop_ms / 1000)
    hop_samples = max(1, hop_samples)

    # SciPy requires the FFT size to be at least the window length.
    # MVIEW/MATLAB allows fft(x, n) where n < len(x), which effectively
    # truncates; this implementation intentionally does not reproduce that.
    fft_samples = max(frame * 2, nperseg)

    # Idiomatic STFT windowing uses the periodic window form.
    # MVIEW uses MATLAB hamming(n), which is closer to sym=True.
    win = windows.hamming(nperseg, sym=True)
    stft = ShortTimeFFT(
        win=win,
        hop=hop_samples,
        fs=traj.sample_rate_hz,
        mfft=fft_samples,
        scale_to="magnitude",
    )

    S = stft.spectrogram(signal)
    S_db = 20 * np.log10(S + np.finfo(float).eps)
    return S_db


@overload
def get_rms(
    traj: Trajectory | Audio, win_ms: float, time_s: None = None
) -> NDArray[np.float64]: ...


@overload
def get_rms(traj: Trajectory | Audio, win_ms: float, time_s: float) -> float: ...


def get_rms(
    traj: Trajectory | Audio, win_ms: float, time_s: float | None = None
) -> NDArray[np.float64] | float:
    window = max(1, round(traj.sample_rate_hz * win_ms / 1000))
    data = traj.data if isinstance(traj, Trajectory) else traj.signal

    if time_s is not None:
        center = int(np.floor(time_s * traj.sample_rate_hz))
        head = center - round(window / 2)
        head = max(0, head)
        tail = head + window
        if tail > traj.n_samples:
            tail = traj.n_samples
            head = max(0, tail - window)

        s = data[head:tail]
        return float(np.sqrt(np.mean(s**2)))

    b = np.ones(window) / window
    rms: NDArray[np.float64] = np.sqrt(np.abs(filtfilt(b, [1], data**2)))
    return rms


@overload
def get_zc(
    traj: Trajectory | Audio, win_ms: float, time_s: None = None
) -> NDArray[np.float64]: ...


@overload
def get_zc(traj: Trajectory | Audio, win_ms: float, time_s: float) -> float: ...


def get_zc(
    traj: Trajectory | Audio, win_ms: float, time_s: float | None = None
) -> NDArray[np.float64] | float:
    window = max(1, round(traj.sample_rate_hz * win_ms / 1000))
    data = traj.data if isinstance(traj, Trajectory) else traj.signal

    if time_s is not None:
        center = int(np.floor(time_s * traj.sample_rate_hz))
        head = center - round(window / 2)
        head = max(0, head)
        tail = head + window
        if tail > traj.n_samples:
            tail = traj.n_samples
            head = max(0, tail - window)

        s = data[head:tail]
        return float(np.sum(np.abs(np.diff(s >= 0))))

    wl2 = int(np.ceil(window / 2))
    s = np.concatenate([np.zeros(wl2), data, np.zeros(wl2)])
    zc = cast(
        NDArray[np.float64],
        lfilter(np.ones(window), [1], np.concatenate([[0], np.abs(np.diff(s >= 0))])),
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


def analyze_audio(traj: Trajectory, config: AppConfig):
    S_db = get_spect(
        traj,
        frame=config.fft_eval_points,
        # TODO: is this right? This is what MVIEW does but I think it should be analysis_window_ms
        win_ms=config.averaging_window_ms,
        hop_ms=config.overlap_ms,
        mult=config.spectrogram_bandwidth_mode.value,
    )
    rms = get_rms(traj, win_ms=config.analysis_window_ms)
    zc = get_zc(traj, win_ms=config.analysis_window_ms)
    f0 = get_f0(traj)
    return Audio(
        name=traj.name,
        sample_rate_hz=traj.sample_rate_hz,
        n_samples=traj.n_samples,
        signal=np.ravel(traj.data),
        spect=S_db,
        rms=rms,
        rms_db=20 * np.log10(rms + np.finfo(float).eps),
        zc=zc,
        f0=f0,
        formants=[],  # TODO: implement
    )


def get_plotting_data(var: DatasetVariable, spec: TrajDisplay, config: AppConfig):
    # Fast path: reuse precomputed audio data
    if var.audio_traj and spec.traj_name == var.audio_traj.name:
        traj = var.audio_traj
        t = np.arange(traj.n_samples) / traj.sample_rate_hz
        match spec.content:
            case "SIGNAL":
                return t, traj.signal
            case "SPECT":
                return (t[0], t[-1], 0, traj.sample_rate_hz / 2), traj.spect
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
            return (t[0], t[-1], 0, traj.sample_rate_hz / 2), get_spect(
                traj,
                frame=config.fft_eval_points,
                win_ms=config.averaging_window_ms,
                hop_ms=config.overlap_ms,
                mult=config.spectrogram_bandwidth_mode.value,
            )
        case "SIGNAL" | "MOVEMENT":
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
            return t, get_rms(traj, win_ms=config.analysis_window_ms)
        case "ZC":
            return t, get_zc(traj, win_ms=config.analysis_window_ms)
        case "movement" | "velocity" | "acceleration":
            cols = [{"x": 0, "y": 1, "z": 2}[comp] for comp in spec.components]
            ps = traj.data[:, cols]
            if spec.content == "movement":
                return t, ps
            vs = np.gradient(ps, axis=0) * traj.sample_rate_hz
            if spec.content == "velocity":
                if vs.shape[1] == config.dimensions:
                    # Collapse if viewing all components
                    # TODO: currently this way for mview compatibility, but I think
                    # "velocity" and "speed" should be separate content types
                    # Otherwise there's this inconsistency
                    return t, np.array([np.linalg.norm(vs, axis=1)]).T
                return t, vs
            accs = np.gradient(vs, axis=0) * traj.sample_rate_hz
            if accs.shape[1] == config.dimensions:
                return t, np.array([np.linalg.norm(accs, axis=1)]).T
            return t, accs
        case x:
            raise ValueError(f"Unexpected content type for temporal display: {x}")


@overload
def compute_spline(
    spline_trajs: list[str],
    positions_by_name: dict[str, tuple[float, float]],
    polyline_spline: bool,
) -> tuple[NDArray[np.float64], NDArray[np.float64]] | None: ...


@overload
def compute_spline(
    spline_trajs: list[str],
    positions_by_name: dict[str, tuple[float, float, float]],
    polyline_spline: bool,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]] | None: ...


def compute_spline(
    spline_trajs: list[str],
    positions_by_name: (
        dict[str, tuple[float, float]] | dict[str, tuple[float, float, float]]
    ),
    polyline_spline: bool,
):
    is_3d = any(len(pos) == 3 for pos in positions_by_name.values())
    spline_points: list[tuple[float, float]] = []

    for name in spline_trajs:
        if name in positions_by_name:
            # Whacky, just pretend it's 2D
            spline_points.append(cast(tuple[float, float], positions_by_name[name]))
        else:
            raise ValueError(
                f"Spline trajectory '{name}' not found among spatial trajectories"
            )

    if len(spline_points) < 2:
        return None

    p = np.asarray(spline_points, dtype=float)
    k = min(3, len(spline_points) - 1)
    if is_3d:
        x_raw, y_raw, z_raw = p[:, 0], p[:, 1], p[:, 2]
        if polyline_spline:
            return x_raw, y_raw, z_raw

        try:
            tck, _u = splprep([x_raw, y_raw, z_raw], s=0, k=k)
            u_new = np.linspace(0, 1, 100)
            x_new, y_new, z_new = splev(u_new, tck)
            return x_new, y_new, z_new
        except Exception:
            return x_raw, y_raw, z_raw

    else:
        x_raw, y_raw = p[:, 0], p[:, 1]
        if polyline_spline:
            return x_raw, y_raw

        try:
            tck, _u = splprep([x_raw, y_raw], s=0, k=k)
            u_new = np.linspace(0, 1, 100)
            x_new, y_new = splev(u_new, tck)
            return x_new, y_new
        except Exception:
            return x_raw, y_raw
