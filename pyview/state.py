from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
import numpy as np


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
    temporal_map: list[str]
    dpi: float
    spatial_bounds: tuple[float, float, float, float, float, float]
    palate_trace: np.ndarray | None = None
    spline_trajs: list[str] | None = None
    audio_traj: str | None = None
    framing_traj: str | None = None
    cursor_s: float = 0.0

    @property
    def variable_names(self) -> list[str]:
        return list(self.data.keys())

    @property
    def selected_value(self) -> DatasetVariable:
        return self.data[self.selected_variable]
