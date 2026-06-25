from typing import TYPE_CHECKING
from dataclasses import dataclass
from time import time
import math

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import PchipInterpolator
from scipy.signal import butter, filtfilt

from pyview.state import Label, SpatialTrajDisplay, ScalarTrajDisplay
from pyview.lproc.protocol import LabelProcedure, LabelUpdateResult

if TYPE_CHECKING:
    from ..state import Color, TrajDisplay, Trajectory
    from .protocol import LabelPlotContext, LPWindowState


SOURCE_ID = "LP_FINDGEST"


@dataclass
class FindGestConfig:
    f_name: str = "<SCREEN>"
    thrgons: float = 0.2
    thrnons: float = 0.2
    thrnoff: float = 0.2
    thrgoff: float = 0.2
    onsthr: float = 0.2
    offsthr: float = 0.15
    fclp: float = 0.2
    use_filter: bool = False
    plot: bool = False
    delete_boxes: bool = True


@dataclass(frozen=True)
class DelimitGestResult:
    gons: float
    pvel: float
    nons: float
    maxc: float
    noffs: float
    pvel2: float
    goffs: float
    pv: float
    pv2: float
    dist: float
    dist2: float
    stiff: float
    stiff2: float
    pd: float
    pd2: float


@dataclass(frozen=True)
class FindGestRecord:
    label_name: str
    result: DelimitGestResult
    velocity: NDArray[np.float64]
    source_signal: NDArray[np.float64]
    sample_rate_hz: float
    components: list[int]
    traj_name: str
    ax_index: int
    group: float


class FindGestLP(LabelProcedure):
    name = "Find gestures"

    def __init__(self, state: LPWindowState):
        super().__init__(state)
        self.config = FindGestConfig()

    def create_label(self, label, context=None):
        if context is None:
            return LabelUpdateResult()

        if "shift" in context.modifiers:
            return LabelUpdateResult(created_labels=[label])

        traj = self.state.selected_value.trajectories[context.spec.traj_name]
        if traj.kind == "audio":
            return LabelUpdateResult()

        extracted = extract_findgest_signal(traj, context.spec)
        if extracted is None:
            return LabelUpdateResult()

        source_signal, fit_signal, components = extracted
        record = make_findgest_record(
            label.name,
            source_signal,
            fit_signal,
            components,
            traj.name,
            traj.sample_rate_hz,
            label.offset_s,
            self.state.head_s,
            self.state.tail_s,
            context.ax_index,
            self.config,
        )
        if record is None:
            return LabelUpdateResult()

        return LabelUpdateResult(
            created_labels=make_findgest_labels(record, label.color)
        )

    def plot_label(self, label, context):
        rendered = context.plot_default(label)
        record = get_label_record(label)
        if (
            record is None
            or label.lproc_data["name"] != "MAXC"
            or context.ax_index != record.ax_index
        ):
            return rendered

        rendered.artists.extend(
            plot_gesture_box(record, context, self.state.colors[context.spec.traj_name])
        )
        return rendered

    def delete_labels(self, labels):
        return LabelUpdateResult(
            deleted_labels=expand_grouped_deletions(self.state.labels, labels)
        )


def extract_findgest_signal(traj: Trajectory, spec: TrajDisplay):
    source_signal = traj.data
    if source_signal.ndim == 1:
        source_signal = source_signal[:, None]

    if isinstance(spec, SpatialTrajDisplay):
        dim_map = {"x": 0, "y": 1, "z": 2}
        components = [
            dim_map[component]
            for component in spec.components
            if dim_map[component] < source_signal.shape[1]
        ]
    elif isinstance(spec, ScalarTrajDisplay):
        components = [0]
    else:
        return None

    if not components:
        return None

    return source_signal, source_signal[:, components], components


def make_findgest_record(
    label_name: str,
    source_signal: NDArray[np.float64],
    fit_signal: NDArray[np.float64],
    components: list[int],
    traj_name: str,
    sample_rate_hz: float,
    click_s: float,
    head_s: float,
    tail_s: float,
    ax_index: int,
    config: FindGestConfig,
):
    click_idx = int(math.floor(click_s * sample_rate_hz))
    head_idx = int(math.floor(head_s * sample_rate_hz))
    tail_idx = int(math.floor(tail_s * sample_rate_hz))

    result, velocity = delimit_gest(
        fit_signal, click_idx, (head_idx, tail_idx), sample_rate_hz, config
    )
    if result is None:
        return None

    return FindGestRecord(
        label_name=label_name,
        result=result,
        velocity=velocity,
        source_signal=source_signal,
        sample_rate_hz=sample_rate_hz,
        components=components,
        traj_name=traj_name,
        ax_index=ax_index,
        group=time(),
    )


def make_findgest_labels(record: FindGestRecord, color: Color):
    labels = []

    for name, offset_s in gesture_offsets(record.result).items():
        data = {"source": SOURCE_ID, "group": record.group, "name": name}
        if name == "PVEL":
            data = {**data, "record": record}
        elif name == "MAXC":
            data = {**data, "record": record}
        labels.append(
            Label(
                name=f"{record.label_name}:{name}" if record.label_name else name,
                offset_s=offset_s,
                note=record.traj_name,
                color=color,
                lproc_data=data,
            )
        )

    return labels


def gesture_offsets(result: DelimitGestResult):
    return {
        "GONS": result.gons,
        "PVEL": result.pvel,
        "NONS": result.nons,
        "MAXC": result.maxc,
        "NOFFS": result.noffs,
        "PVEL2": result.pvel2,
        "GOFFS": result.goffs,
    }


def delimit_gest(
    s: NDArray[np.float64],
    offs: int,
    ht: tuple[int, int],
    sample_rate_hz: float,
    config: FindGestConfig,
):
    s = np.asarray(s, dtype=float)
    if s.ndim == 1:
        s = s[:, None]

    if s.shape[0] < 4:
        return None, tangential_velocity(s)

    head = max(0, ht[0])
    tail = min(s.shape[0] - 1, ht[1])
    offs = min(max(offs, 0), s.shape[0] - 1)

    vv = tangential_velocity(s)
    v = vv - np.nanmin(vv)
    fv = filtered_velocity(v, config.fclp)
    detect_v = fv if config.use_filter else v

    minima = velocity_minima(fv)
    if len(minima) < 3:
        return None, vv

    n = int(np.argmin(np.abs(minima - offs)))
    if n == 0 or n == len(minima) - 1:
        return None, vv

    maxc = int(minima[n])
    if maxc < head or maxc > tail:
        return None, vv

    max_v = float(np.nanmax(fv[head : tail + 1]))
    if not np.isfinite(max_v) or max_v <= 0:
        return None, vv

    gons = find_valid_left_minimum(fv, minima, n, maxc, head, config.onsthr * max_v)
    goffs = find_valid_right_minimum(fv, minima, n, maxc, tail, config.offsthr * max_v)
    pvel = gons + int(np.nanargmax(detect_v[gons : maxc + 1]))
    pvel2 = maxc + int(np.nanargmax(detect_v[maxc : goffs + 1]))
    maxc = pvel + int(np.nanargmin(detect_v[pvel : pvel2 + 1]))

    gons = threshold_first(
        detect_v,
        gons,
        pvel,
        detect_v[gons] + config.thrgons * (detect_v[pvel] - detect_v[gons]),
    )
    nons = threshold_last(
        detect_v,
        pvel,
        maxc,
        detect_v[maxc] + config.thrnons * (detect_v[pvel] - detect_v[maxc]),
    )
    noffs = threshold_first(
        detect_v,
        maxc,
        pvel2,
        detect_v[maxc] + config.thrnoff * (detect_v[pvel2] - detect_v[maxc]),
    )
    goffs = threshold_last(
        detect_v,
        pvel2,
        goffs,
        detect_v[goffs] + config.thrgoff * (detect_v[pvel2] - detect_v[goffs]),
    )

    if gons is None or nons is None or noffs is None or goffs is None:
        return None, vv

    pv = float(vv[pvel])
    pv2 = float(vv[pvel2])
    dist = path_distance(s[gons : maxc + 1])
    dist2 = path_distance(s[maxc : goffs + 1])
    result = DelimitGestResult(
        gons=gons / sample_rate_hz,
        pvel=pvel / sample_rate_hz,
        nons=nons / sample_rate_hz,
        maxc=maxc / sample_rate_hz,
        noffs=noffs / sample_rate_hz,
        pvel2=pvel2 / sample_rate_hz,
        goffs=goffs / sample_rate_hz,
        pv=pv,
        pv2=pv2,
        dist=dist,
        dist2=dist2,
        stiff=pv / dist if dist != 0 else math.nan,
        stiff2=pv2 / dist2 if dist2 != 0 else math.nan,
        pd=float(np.linalg.norm(s[maxc] - s[gons])),
        pd2=float(np.linalg.norm(s[goffs] - s[maxc])),
    )
    return result, vv


def tangential_velocity(s: NDArray[np.float64]):
    if len(s) < 2:
        return np.zeros(len(s), dtype=float)

    ds = np.empty_like(s)
    ds[0] = s[1] - s[0]
    ds[-1] = s[-1] - s[-2]
    if len(s) > 2:
        ds[1:-1] = s[2:] - s[:-2]

    return np.sqrt(np.sum((ds / 2.0) ** 2, axis=1))


def filtered_velocity(v: NDArray[np.float64], fclp: float):
    v = fix_nan(v)
    cutoff = min(max(float(fclp), 1e-6), 0.999999)
    b, a = butter(3, cutoff)
    return filtfilt(b, a, v)


def fix_nan(s: NDArray[np.float64]):
    s = np.asarray(s, dtype=float).copy()
    missing = np.isnan(s)
    if not np.any(missing):
        return s

    valid = np.where(~missing)[0]
    if len(valid) == 0:
        return s

    if np.isnan(s[0]):
        s[: valid[0]] = s[valid[0]]
    if np.isnan(s[-1]):
        s[valid[-1] + 1 :] = s[valid[-1]]

    valid = np.where(~np.isnan(s))[0]
    missing = np.where(np.isnan(s))[0]
    if len(missing) == 0:
        return s

    starts = missing[np.diff(np.r_[[-2], missing]) > 1]
    for start in starts:
        a = start - 1
        b_candidates = valid[valid > start]
        if len(b_candidates) == 0:
            continue
        b = int(b_candidates[0])
        k = np.arange(a + 1, b)
        interp = PchipInterpolator([a, b], s[[a, b]])
        s[k] = interp(k)

    return s


def velocity_minima(fv: NDArray[np.float64]):
    rising = np.r_[0, np.diff(fv)] > 0
    return np.where(np.diff(rising.astype(int)) > 0)[0]


def find_valid_left_minimum(
    fv: NDArray[np.float64],
    minima: NDArray[np.int64],
    n: int,
    maxc: int,
    head: int,
    threshold: float,
):
    nn = n - 1
    gons = int(minima[nn])
    while nn > 0:
        gons = int(minima[nn])
        if (
            abs(np.nanmax(fv[gons : maxc + 1]) - np.nanmin(fv[gons : maxc + 1]))
            > threshold
        ):
            break
        nn -= 1

    if nn < 1 or gons < head:
        return head

    return gons


def find_valid_right_minimum(
    fv: NDArray[np.float64],
    minima: NDArray[np.int64],
    n: int,
    maxc: int,
    tail: int,
    threshold: float,
):
    nn = n + 1
    goffs = int(minima[nn])
    while nn < len(minima):
        goffs = int(minima[nn])
        if (
            abs(np.nanmax(fv[maxc : goffs + 1]) - np.nanmin(fv[maxc : goffs + 1]))
            > threshold
        ):
            break
        nn += 1

    if nn >= len(minima) or goffs > tail:
        return tail

    return goffs


def threshold_first(v: NDArray[np.float64], start: int, end: int, threshold: float):
    hits = np.where(v[start : end + 1] > threshold)[0]
    if len(hits) == 0:
        return None

    return start + int(hits[0])


def threshold_last(v: NDArray[np.float64], start: int, end: int, threshold: float):
    hits = np.where(v[start : end + 1] > threshold)[0]
    if len(hits) == 0:
        return None

    return start + int(hits[-1])


def path_distance(s: NDArray[np.float64]):
    if len(s) < 2:
        return 0.0

    return float(np.sum(np.sqrt(np.sum(np.diff(s, axis=0) ** 2, axis=1))))


def get_label_record(label: Label):
    data = label.lproc_data
    if not isinstance(data, dict) or data.get("source") != SOURCE_ID:
        return None

    record = data.get("record")
    if not isinstance(record, FindGestRecord):
        return None

    return record


def plot_gesture_box(record: FindGestRecord, context: LabelPlotContext, color: Color):
    result = record.result
    y0, y1 = context.ax.get_ylim()
    center = y0 + 0.5 * (y1 - y0)
    half_height = 0.5 * result.pd
    y = [
        center - half_height,
        center + half_height,
        center + half_height,
        center - half_height,
        center - half_height,
    ]

    outer = context.ax.plot(
        [result.gons, result.gons, result.goffs, result.goffs, result.gons],
        y,
        color=color,
        linewidth=2.0,
        zorder=998,
    )
    inner = context.ax.fill(
        [result.nons, result.nons, result.noffs, result.noffs, result.nons],
        y,
        color=color,
        alpha=0.25,
        zorder=997,
    )
    maxc = context.ax.plot(
        [result.maxc, result.maxc],
        y[:2],
        color="white",
        linestyle="--",
        linewidth=1.0,
        zorder=999,
    )

    return [*outer, inner[0], *maxc]


def expand_grouped_deletions(
    labels: tuple[Label, ...] | list[Label], selected: list[int]
):
    groups = set()
    deleted = set(selected)

    for idx in selected:
        data = labels[idx].lproc_data
        if isinstance(data, dict) and data.get("source") == SOURCE_ID:
            groups.add(data.get("group"))

    for idx, label in enumerate(labels):
        data = label.lproc_data
        if (
            isinstance(data, dict)
            and data.get("source") == SOURCE_ID
            and data.get("group") in groups
        ):
            deleted.add(idx)

    return sorted(deleted)
