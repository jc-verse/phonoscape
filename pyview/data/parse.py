from pathlib import Path
import re
from fnmatch import fnmatch
from typing import TypedDict, Literal

import numpy as np
import matplotlib.pyplot as plt
from scipy.io import loadmat

from ..state import (
    DatasetVariable,
    Trajectory,
    TrajDisplay,
    ScalarTrajDisplay,
    SpatialTrajDisplay,
    PyViewConfig,
)


class PyViewArgs(TypedDict, total=False):
    palate: str | None
    spline: list[str] | None
    audio: str | None
    framing: str | None
    temporal_disp_trajs: list[str] | None


def load_variables(
    file: str | Path, variables_pattern: str = "*"
) -> tuple[dict[str, DatasetVariable], dict[str, np.ndarray]]:
    raw = loadmat(file, squeeze_me=True)

    raw = {k: v for k, v in raw.items() if not k.startswith("__")}
    data = {k: v for k, v in raw.items() if v.dtype.names is not None}
    other = {k: v for k, v in raw.items() if v.dtype.names is None}

    if variables_pattern != "*":
        data = {k: v for k, v in data.items() if fnmatch(k, variables_pattern)}

    structured_data: dict[str, DatasetVariable] = {}
    for k, v in data.items():
        trajectories: dict[str, Trajectory] = {}
        estimated_durations = []
        prop_cycle = plt.rcParams["axes.prop_cycle"]
        colors = prop_cycle.by_key()["color"]
        colors_iter = iter(colors)
        for name, srate, signal in zip(v["NAME"], v["SRATE"], v["SIGNAL"]):
            name = str(name).strip().upper()
            if signal.ndim == 0:
                raise ValueError(
                    f"Don't know how to process scalar trajectory {k}/{name}"
                )
            elif signal.ndim > 2:
                raise ValueError(
                    f"Don't know how to process trajectory with >2 dims: {k}/{name}"
                )
            kind = "spatial" if signal.ndim == 2 else "scalar"
            trajectories[name] = Trajectory(
                name=name,
                kind=kind,
                color=(
                    plt.rcParams["text.color"]
                    if kind == "scalar"
                    else next(colors_iter)
                ),
                sample_rate_hz=float(srate),
                dimensions=1 if signal.ndim == 1 else signal.shape[1],
                n_samples=signal.shape[0],
                data=signal,
            )
            estimated_durations.append(signal.shape[0] / float(srate))
        structured_data[k] = DatasetVariable(
            name=k,
            duration_ms=max(estimated_durations) if estimated_durations else 0.0,
            trajectories=trajectories,
        )

    return structured_data, other


def parse_trajectory_display_spec(
    name: str, first_variable: DatasetVariable
) -> TrajDisplay:
    if match := re.match(r"^(.*)_(SPECT|F0|RMS|ZC|VEL|ABSVEL)$", name):
        base_name, content = match.groups()
        if (
            base_name in first_variable.trajectories
            and first_variable.trajectories[base_name].kind == "scalar"
        ):
            return ScalarTrajDisplay(traj_name=base_name, content=content)
        else:
            raise ValueError(
                f"Trajectory '{name}' does not match any known scalar trajectory for variable '{first_variable.name}'"
            )
    match = re.match(r"^([va])?(.*?)(x)?(y)?(z)?$", name)
    if not match:
        raise Exception(f"Unexpected non-match")
    content, base_name, x, y, z = match.groups()
    if (
        base_name in first_variable.trajectories
        and first_variable.trajectories[base_name].kind == "spatial"
    ):
        components: list[Literal["x", "y", "z"]] = []
        if x:
            components.append("x")
        if y:
            components.append("y")
        if z:
            components.append("z")
        if not components:
            components = ["x", "y", "z"]
        return SpatialTrajDisplay(
            traj_name=base_name,
            content=(
                "velocity"
                if content == "v"
                else "acceleration" if content == "a" else "movement"
            ),
            components=components,
        )
    elif (
        base_name in first_variable.trajectories
        and first_variable.trajectories[base_name].kind == "scalar"
    ):
        if content or x or y or z:
            raise ValueError(f"Trajectory '{base_name}' is scalar")
        return ScalarTrajDisplay(traj_name=base_name, content="SIGNAL")
    else:
        raise ValueError(
            f"Trajectory '{name}' does not match any known trajectory for variable '{first_variable.name}'"
        )


def normalize_args(
    args: PyViewArgs,
    data: dict[str, DatasetVariable],
    other_data: dict[str, np.ndarray],
) -> PyViewConfig:
    first_variable = next(iter(data.values()))

    audio_traj = args.get("audio")
    if audio_traj is None:
        audio_traj = next(
            (
                name
                for name, traj in first_variable.trajectories.items()
                if traj.sample_rate_hz > 1000 and traj.kind == "scalar"
            ),
            None,
        )
    else:
        audio_traj = audio_traj.upper()
        if audio_traj not in first_variable.trajectories:
            raise ValueError(
                f"Audio trajectory '{audio_traj}' not found among trajectories of variable '{first_variable.name}'"
            )
        if first_variable.trajectories[audio_traj].kind != "scalar":
            raise ValueError(f"Audio trajectory '{audio_traj}' found but is not scalar")

    temporal_disp_trajs = args.get("temporal_disp_trajs")
    if temporal_disp_trajs is None:
        temporal_disp_trajs = list(first_variable.trajectories.keys())
        if audio_traj:
            temporal_disp_trajs.remove(audio_traj)
            temporal_disp_trajs = [
                audio_traj,
                f"{audio_traj}_SPECT",
            ] + temporal_disp_trajs
    temporal_disp_specs = [
        parse_trajectory_display_spec(name, first_variable)
        for name in temporal_disp_trajs
    ]

    palate_variable = args.get("palate")
    palate_trace = None
    if palate_variable is not None:
        palate_trace = other_data[palate_variable]
        del other_data[palate_variable]

    spline_trajs = args.get("spline")
    if spline_trajs is None:
        spline_trajs = [
            name for name in first_variable.trajectories if name.startswith("T")
        ]
    else:
        spline_trajs = [name.upper() for name in spline_trajs]
        for name in spline_trajs:
            for variable in data.values():
                if name not in variable.trajectories:
                    raise ValueError(
                        f"Spline trajectory '{name}' not found in variable '{variable.name}'"
                    )

    framing_traj = args.get("framing", audio_traj)
    if framing_traj is None:
        framing_traj = next(iter(first_variable.trajectories.keys()))

    return PyViewConfig(
        palate_trace=palate_trace,
        spline_trajs=spline_trajs,
        audio_traj=audio_traj,
        framing_traj=framing_traj,
        temporal_disp_specs=temporal_disp_specs,
    )
