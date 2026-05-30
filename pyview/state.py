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
    content: Literal["SIGNAL", "SPECT", "F0", "RMS", "ZC", "VEL", "ABSVEL"]

    def __str__(self) -> str:
        if self.content == "SIGNAL":
            return self.traj_name
        else:
            return f"{self.traj_name}_{self.content}"


@dataclass
class SpatialTrajDisplay:
    traj_name: str
    content: Literal["movement", "velocity", "acceleration"]
    components: list[Literal["x", "y", "z"]]

    def __str__(self) -> str:
        comp_str = "".join(self.components)
        if comp_str == "xyz":
            comp_str = ""
        prefix = {"movement": "", "velocity": "v", "acceleration": "a"}[self.content]
        return f"{prefix}{self.traj_name}{comp_str}"


TrajDisplay = ScalarTrajDisplay | SpatialTrajDisplay


@dataclass
class Trajectory:
    name: str
    kind: Literal["scalar", "spatial"]
    color: str
    sample_rate_hz: float
    dimensions: int
    n_samples: int
    # TODO: migrate to a storage ref?
    data: np.ndarray


@dataclass
class DatasetVariable:
    name: str
    duration_ms: float
    trajectories: dict[str, Trajectory]
    # embedded_labels


@dataclass
class PyViewState:
    file: Path
    variables_pattern: str
    data: dict[str, DatasetVariable]
    other_data: dict[str, Any]
    selected_variable: str
    dpi: float
    spatial_bounds: tuple[float, float, float, float, float, float]
    config: PyViewConfig
    cursor_s: float

    @property
    def variable_names(self) -> list[str]:
        return list(self.data.keys())

    @property
    def selected_value(self) -> DatasetVariable:
        return self.data[self.selected_variable]
