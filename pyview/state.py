from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
import numpy as np


@dataclass
class PyViewConfig:
    palate_trace: np.ndarray | None
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
    data: np.ndarray
    angles: np.ndarray | None


@dataclass(frozen=True)
class F0Track:
    sample_rate_hz: float
    raw_hz: np.ndarray
    interp_hz: np.ndarray
    voiced_flag: np.ndarray
    voiced_prob: np.ndarray


@dataclass
class Audio:
    name: str
    sample_rate_hz: float
    n_samples: int
    signal: np.ndarray
    spect: tuple[Any, np.ndarray]
    rms: np.ndarray
    rms_db: np.ndarray
    zc: np.ndarray
    f0: F0Track
    l1: np.ndarray
    skew: np.ndarray
    kurt: np.ndarray
    formants: list[tuple[np.ndarray, np.ndarray]]


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

    def edit_label(self, label_idx: int, name: str, offset_s: float, note: str):
        old_label = self.labels[label_idx]
        new_label = Label(name=name, offset_s=offset_s, note=note)
        self.labels[label_idx] = new_label
        return new_label, old_label

    def delete_labels(self, label_idx: list[int]):
        return [self.labels.pop(i) for i in sorted(label_idx, reverse=True)]
