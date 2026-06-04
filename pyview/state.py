from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
import numpy as np
from PySide6.QtCore import QObject, Signal


class StringVar(QObject):
    changed = Signal(str)

    def __init__(self, value: str = ""):
        super().__init__()
        self._value = value

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        if value == self._value:
            return
        self._value = value
        self.changed.emit(value)


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
    # TODO: should I implement "F0"?
    # The mview version is buggy
    content: Literal["SIGNAL", "SPECT", "RMS", "ZC", "VEL", "ABSVEL"]

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


@dataclass
class DatasetVariable:
    name: str
    duration_s: float
    trajectories: dict[str, Trajectory]
    # embedded_labels


@dataclass(frozen=True, eq=True)
class Label:
    name: str
    offset_s: float
    # MVIEW calls this "hook"
    note: str


@dataclass
class PyViewState:
    file: Path
    variables_pattern: str
    data: dict[str, DatasetVariable]
    other_data: dict[str, Any]
    labels: list[Label]
    # Precomputed because it's also used for the spectrogram cross-section.
    # Avoids two FFTs, one for each view.
    audio_spect: tuple[Any, np.ndarray] | None
    selected_variable: str
    dpi: float
    dimensions: Literal[2, 3]
    spatial_bounds: (
        tuple[float, float, float, float, float, float]
        | tuple[float, float, float, float]
    )
    config: PyViewConfig
    cursor_s: float
    head_s: float
    tail_s: float
    play_mode: StringVar
    # TODO: should this be configurable? Should this have a minimum of 1/sr?
    min_sel_dur_s: float = 0.025

    @property
    def variable_names(self) -> list[str]:
        return list(self.data.keys())

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
