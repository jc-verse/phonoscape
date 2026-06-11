from typing import cast, Literal
from dataclasses import dataclass

from amfm_decompy import basic_tools
from amfm_decompy import pYAAPT
import numpy as np
from numpy.typing import NDArray
from scipy.signal import ShortTimeFFT, windows, filtfilt, lfilter


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
    extent = (0.0, traj.n_samples / traj.sample_rate_hz, 0.0, traj.sample_rate_hz / 2)
    return extent, S_db, hop / traj.sample_rate_hz


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


@dataclass(frozen=True)
class CogMeasure:
    l1: float
    skew: float
    kurt: float


def get_cog(
    traj: Audio,
    time_s: float,
    alg: Literal["AVG", "WIN"] = "AVG",
    spec: Literal["MAG", "POW"] = "MAG",
    preemp: float | None = 1.0,
    cutoff_hz: float | None = None,
    window_ms: float = 50.0,
    frame: int | None = None,
    avg_window_ms: float = 6.0,
    overlap_ms: float = 1.0,
) -> CogMeasure:
    # MATLAB cog takes time in milliseconds:
    # ts = floor(t * sr / 1000) + 1
    ts = int(np.floor(time_s * traj.sample_rate_hz))

    ns = max(1, round(window_ms / 1000.0 * traj.sample_rate_hz))
    head = ts - round(ns / 2.0)

    if head < 0:
        head = 0

    tail = head + ns
    if tail > traj.n_samples:
        tail = traj.n_samples
        head = max(0, tail - ns)

    s = traj.signal[head:tail].copy()

    # MATLAB default PREEMP is 1. Passing None corresponds to PREEMP=[],
    # i.e. adaptive pre-emphasis.
    if preemp is None:
        r0 = np.dot(s, s)
        if r0 <= np.finfo(float).eps:
            mu = 0.0
        else:
            r1 = np.dot(s, np.concatenate([[0.0], s[:-1]]))
            mu = r1 / r0
            if mu < 0:
                mu = 0.0
    else:
        mu = preemp

    if not 0 <= mu <= 1:
        raise ValueError(f"pre-emphasis coefficient error ({mu:g})")

    if mu > 0:
        s = lfilter([1.0, -mu], [1.0], s)

    if frame is None:
        frame = 2 ** int(np.floor(np.log2(ns)))

    use_power = spec.upper() == "POW"

    if alg.upper() == "AVG":
        avg_w = max(1, int(np.floor(avg_window_ms * traj.sample_rate_hz / 1000.0)))
        shift = max(1, int(np.floor(overlap_ms * traj.sample_rate_hz / 1000.0)))

        n_frames = round(s.size / shift) + 1
        window = np.hamming(avg_w)

        sx = np.concatenate([np.zeros(avg_w), s, np.zeros(avg_w)])
        si = int(np.ceil(avg_w / 2.0)) - 1

        spectra = np.zeros((frame, n_frames), dtype=np.float64)

        for fi in range(n_frames):
            chunk = sx[si : si + avg_w]
            if chunk.size < avg_w:
                chunk = np.pad(chunk, (0, avg_w - chunk.size))

            fft_vals = np.fft.fft(window * chunk, n=frame * 2)

            if use_power:
                p = np.real(fft_vals) ** 2 + np.imag(fft_vals) ** 2
            else:
                p = np.abs(fft_vals)

            spectra[:, fi] = p[:frame]
            si += shift

        p = spectra.mean(axis=1)

    elif alg.upper() == "WIN":
        window = np.hanning(ns)

        if s.size < ns:
            chunk = np.pad(s, (0, ns - s.size))
        else:
            chunk = s[:ns]

        fft_vals = np.fft.fft(window * chunk, n=frame * 2)

        if use_power:
            p = np.real(fft_vals[:frame]) ** 2 + np.imag(fft_vals[:frame]) ** 2
        else:
            p = np.abs(fft_vals[:frame])

    else:
        raise ValueError(f"unrecognized COG algorithm: {alg}")

    if cutoff_hz is None:
        cutoff_hz = traj.sample_rate_hz / 2.0

    upb = min(frame, round(cutoff_hz * frame * 2.0 / traj.sample_rate_hz))

    if upb <= 1:
        return CogMeasure(l1=np.nan, skew=np.nan, kurt=np.nan)

    p_cut = p[:upb]
    total = np.sum(p_cut)

    if total <= 0 or not np.isfinite(total):
        return CogMeasure(l1=np.nan, skew=np.nan, kurt=np.nan)

    # MATLAB normalizes including DC, then drops DC from the moment calculation.
    p_norm = p_cut / total
    p_norm = p_norm[1:]

    freqs = (
        np.linspace(1, upb, upb - 1, dtype=np.float64)
        * traj.sample_rate_hz
        / (frame * 2.0)
    )

    l1 = np.sum(freqs * p_norm)

    centered = freqs - l1
    l2 = np.sum(centered**2 * p_norm)
    l3 = np.sum(centered**3 * p_norm)
    l4 = np.sum(centered**4 * p_norm)

    if l2 <= 0 or not np.isfinite(l2):
        return CogMeasure(l1=l1, skew=np.nan, kurt=np.nan)

    skew = l3 / (l2**1.5)
    kurt = l4 / (l2**2) - 3.0

    return CogMeasure(l1=l1, skew=skew, kurt=kurt)


def analyze_audio(traj: Trajectory):
    extent, S_db, delta_t = get_spect(traj)
    rms = get_rms(traj)
    zc = get_zc(traj)
    f0 = get_f0(traj)
    return Audio(
        name=traj.name,
        sample_rate_hz=traj.sample_rate_hz,
        n_samples=traj.n_samples,
        signal=np.ravel(traj.data),
        spect=S_db,
        spect_extent=extent,
        spect_delta_t_s=delta_t,
        rms=rms,
        rms_db=20 * np.log10(rms + np.finfo(float).eps),
        zc=zc,
        f0=f0,
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
                return traj.spect_extent, traj.spect
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
            return get_spect(traj)[0:2]
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
