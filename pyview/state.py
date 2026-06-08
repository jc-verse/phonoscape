from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Unpack, TypedDict
import numpy as np
from numpy.typing import NDArray


@dataclass
class PyViewConfig:
    palate_trace: NDArray[np.float64] | None
    spline_trajs: list[str]
    audio_traj: str | None
    framing_traj: str
    temporal_disp_specs: list[TrajDisplay]


@dataclass
class ScalarTrajDisplay:
    traj_name: str
    content: Literal["SIGNAL", "SPECT", "RMS", "ZC", "F0", "VEL", "ABSVEL"]

    def __str__(self) -> str:
        if self.content == "SIGNAL":
            return self.traj_name
        else:
            return f"{self.traj_name}_{self.content}"


@dataclass
class SpatialTrajDisplay:
    traj_name: str
    traj_dims: int
    content: Literal["movement", "velocity", "acceleration"]
    components: list[Literal["x", "y", "z"]]

    def __str__(self) -> str:
        comp_str = "".join(self.components)
        if (
            self.traj_dims == 3
            and comp_str == "xyz"
            or self.traj_dims == 2
            and comp_str == "xy"
        ):
            comp_str = ""
        prefix = {"movement": "", "velocity": "v", "acceleration": "a"}[self.content]
        return f"{prefix}{self.traj_name}{comp_str}"


TrajDisplay = ScalarTrajDisplay | SpatialTrajDisplay


@dataclass
class Trajectory:
    name: str
    kind: Literal["scalar", "spatial"]
    sample_rate_hz: float
    n_samples: int
    color: str | tuple[float, float, float]
    data: NDArray[np.float64]
    angles: NDArray[np.float64] | None


@dataclass(frozen=True)
class F0Track:
    sample_rate_hz: float
    raw_hz: NDArray[np.float64]
    interp_hz: NDArray[np.float64]


@dataclass
class Audio:
    name: str
    sample_rate_hz: float
    n_samples: int
    signal: NDArray[np.float64]
    spect: tuple[list[float], NDArray[np.float64]]
    # TODO: lazily compute only if requested (by temporal view or "report")
    rms: NDArray[np.float64]
    rms_db: NDArray[np.float64]
    zc: NDArray[np.float64]
    f0: F0Track
    formants: list[tuple[NDArray[np.float64], NDArray[np.float64]]]


@dataclass
class DatasetVariable:
    name: str
    duration_s: float
    trajectories: dict[str, Trajectory]
    audio_traj: Audio | None


@dataclass(frozen=True, eq=True)
class Label:
    name: str
    offset_s: float
    # MVIEW calls this "hook"
    note: str


class LabelEdit(TypedDict, total=False):
    name: str
    offset_s: float
    note: str


@dataclass
class PyViewState:
    file: Path
    data: dict[str, DatasetVariable]
    other_data: dict[str, Any]
    custom: dict[str, tuple[str, Any]]
    labels: list[Label]
    selected_variable: str
    dimensions: Literal[2, 3]
    spatial_bounds: (
        tuple[float, float, float, float, float, float]
        | tuple[float, float, float, float]
    )
    config: PyViewConfig
    cursor_s: float
    head_s: float
    tail_s: float
    play_mode: str
    # TODO: should this be configurable? Should this have a minimum of 1/sr?
    min_sel_dur_s: float = 0.025

    @property
    def selected_value(self) -> DatasetVariable:
        return self.data[self.selected_variable]

    def add_label(self, name: str, offset_s: float, note: str):
        new_label = Label(name=name, offset_s=offset_s, note=note)
        self.labels.append(new_label)
        return new_label

    def edit_label(
        self, label_idx: int, **kwargs: Unpack[LabelEdit]
    ) -> tuple[Label, Label]:
        old_label = self.labels[label_idx]
        new_label = Label(**{**vars(old_label), **kwargs})
        self.labels[label_idx] = new_label
        return new_label, old_label

    def delete_labels(self, label_idx: list[int]):
        return [self.labels.pop(i) for i in sorted(label_idx, reverse=True)]
