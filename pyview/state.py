from dataclasses import dataclass
from enum import IntFlag, Enum, auto
from pathlib import Path
from typing import Any, Literal, Unpack, TypedDict, cast
import numpy as np
from numpy.typing import NDArray


class ActiveAnalysis(IntFlag):
    NONE = 0
    LPC = auto()
    DFT = auto()
    AVG = auto()
    CEPS = auto()


class SpectrogramBandwidth(Enum):
    WIDE = 1
    MID_1 = 2
    MID_2 = 3
    NARROW = 4


@dataclass
class AppConfig:
    file: Path
    data: dict[str, DatasetVariable]
    other_data: dict[str, Any]
    palate_trace: NDArray[np.float64] | None
    pharynx_trace: NDArray[np.float64] | None
    spline_trajs: list[str]
    polyline_spline: bool
    audio_traj: str | None
    framing_traj: str
    spatial_bounds: (
        tuple[float, float, float, float]
        | tuple[float, float, float, float, float, float]
    )
    spatial_exclude: list[str]
    dimensions: Literal[2, 3]

    # Movement
    nudge_step_ms: float = 5.0
    playback_rate: float = 1.0

    # Spectral analysis
    active_analyses: ActiveAnalysis = ActiveAnalysis.LPC
    analysis_window_ms: float = 30.0
    lpc_order: int = 26  # Need overriding based on sample rate
    fft_eval_points: int = 256
    averaging_window_ms: float = 6.0
    overlap_ms: float = 1.0
    spl_reference_db: float = 20.0
    spectral_display_cutoff_hz: float = 11025.0  # Need overriding based on sample rate
    pre_emphasis: float | None = 0.98
    is_female: bool = False
    spectrogram_bandwidth_mode: SpectrogramBandwidth = SpectrogramBandwidth.WIDE


@dataclass
class AudioTrajDisplay:
    traj_name: str
    content: Literal["SIGNAL", "SPECT", "RMS", "ZC", "F0"]

    def __str__(self) -> str:
        if self.content == "SIGNAL":
            return self.traj_name
        else:
            return f"{self.traj_name}_{self.content}"


@dataclass
class ScalarTrajDisplay:
    traj_name: str
    content: Literal["MOVEMENT", "VEL", "ABSVEL"]

    def __str__(self) -> str:
        if self.content == "MOVEMENT":
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


TrajDisplay = AudioTrajDisplay | ScalarTrajDisplay | SpatialTrajDisplay


@dataclass
class Trajectory:
    name: str
    kind: Literal["audio", "scalar", "spatial"]
    sample_rate_hz: float
    n_samples: int
    # As specified in the dataset
    color: str | tuple[float, float, float] | None
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
    spect: NDArray[np.float64]
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
class WindowState:
    custom: dict[str, tuple[str, Any]]
    labels: list[Label]
    selected_variable: str
    temporal_disp_specs: list[TrajDisplay]
    # Actually used (with defaults/customization/inheritance)
    colors: dict[str, str | tuple[float, float, float]]
    app_config: AppConfig
    view: tuple[float, float, float]
    common_scaling: tuple[float, float, float] | None
    cursor_s: float
    head_s: float
    tail_s: float
    play_mode: str
    # TODO: should this be configurable? Should this have a minimum of 1/sr?
    min_sel_dur_s: float = 0.025

    @property
    def selected_value(self) -> DatasetVariable:
        return self.app_config.data[self.selected_variable]

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


def get_component_names(dimensions: int):
    return cast(list[Literal["x", "y", "z"]], ["x", "y", "z"][:dimensions])
