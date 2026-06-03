from pathlib import Path
import re
from fnmatch import fnmatch
from typing import TypedDict, Literal, cast

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
    comps: int | list[int] | None


def get_optional(arr: np.ndarray, name: str) -> np.ndarray | list[None]:
    if name in arr.dtype.names:
        return arr[name]
    else:
        return [None] * len(arr)


def normalize_traj_name(name: str) -> str:
    return str(name).strip().upper().replace("_", "")


def load_variables(
    file: str | Path, variables_pattern: str, comps: int | list[int] | None
) -> tuple[dict[str, DatasetVariable], dict[str, np.ndarray], int]:
    raw = loadmat(file, squeeze_me=True)

    raw = {k: v for k, v in raw.items() if not k.startswith("__")}
    data = {k: v for k, v in raw.items() if v.dtype.names is not None}
    other = {k: v for k, v in raw.items() if v.dtype.names is None}

    if variables_pattern != "*":
        data = {k: v for k, v in data.items() if fnmatch(k, variables_pattern)}

    structured_data: dict[str, DatasetVariable] = {}
    seen_dimensions = set()
    for k, v in data.items():
        trajectories: dict[str, Trajectory] = {}
        estimated_durations = []
        prop_cycle = plt.rcParams["axes.prop_cycle"]
        colors = prop_cycle.by_key()["color"]
        colors_iter = iter(colors)
        for name, srate, signal, color, nComps, angles in zip(
            v["NAME"],
            v["SRATE"],
            v["SIGNAL"],
            get_optional(v, "COLOR"),
            get_optional(v, "NCOMPS"),
            get_optional(v, "ANGLES"),
        ):
            name = normalize_traj_name(name)
            if signal.ndim == 0 or signal.ndim > 2:
                raise ValueError(
                    f"Don't know how to process trajectory not in the shape of [n_samples × n_dims]: {k}/{name}"
                )
            kind = "spatial" if signal.ndim == 2 else "scalar"
            if nComps is None:
                nComps = comps or (
                    list(range(max(3, signal.shape[1]))) if signal.ndim == 2 else [0]
                )
            if np.isscalar(nComps):
                nComps = list(range(nComps))
            else:
                nComps = list(nComps)
            if signal.ndim == 2:
                if max(nComps) >= signal.shape[1]:
                    raise ValueError(
                        f"NCOMPS {nComps} is invalid for trajectory with shape {signal.shape}"
                    )
                elif len(set(nComps)) != len(nComps):
                    raise ValueError(f"NCOMPS {nComps} contains duplicates")
                elif len(nComps) > 3 or len(nComps) < 2:
                    raise ValueError(
                        f"NCOMPS {nComps} must specify 2 or 3 dimensions for spatial trajectory"
                    )
                signal = signal[:, nComps]
                remaining_comps = set(range(signal.shape[1])) - set(nComps)
                if angles is None and remaining_comps:
                    angles = signal[:, list(remaining_comps)]
            trajectories[name] = Trajectory(
                name=name,
                kind=kind,
                sample_rate_hz=float(srate),
                n_samples=signal.shape[0],
                color=(
                    tuple(color)
                    if color is not None
                    else (
                        plt.rcParams["text.color"]
                        if kind == "scalar"
                        else next(colors_iter)
                    )
                ),
                data=signal,
                angles=angles,
            )
            estimated_durations.append(signal.shape[0] / float(srate))
        seen_dimensions.add(
            max(
                traj.data.shape[1]
                for traj in trajectories.values()
                if traj.kind == "spatial"
            )
        )
        structured_data[k] = DatasetVariable(
            name=k,
            duration_s=min(estimated_durations) if estimated_durations else 0.0,
            trajectories=trajectories,
        )
    seen_dimensions.discard(0)
    if len(seen_dimensions) > 1:
        raise ValueError(
            f"Mix of 2D and 3D spatial trajectories found across variables. Please specify --comps to disambiguate."
        )

    return structured_data, other, next(iter(seen_dimensions)) if seen_dimensions else 2


def parse_trajectory_display_spec(
    name: str, first_variable: DatasetVariable, dimensions: int
) -> TrajDisplay:
    if match := re.match(r"^(.*)_(SPECT|RMS|ZC|VEL|ABSVEL)$", name):
        base_name, content = match.groups()
        if (
            base_name in first_variable.trajectories
            and first_variable.trajectories[base_name].kind == "scalar"
        ):
            return ScalarTrajDisplay(
                traj_name=base_name,
                content=cast(Literal["SPECT", "RMS", "ZC", "VEL", "ABSVEL"], content),
            )
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
            if dimensions < 3:
                raise ValueError(
                    f"Trajectory '{name}' specifies z component but data has only {dimensions} dimensions"
                )
            components.append("z")
        if not components:
            components = ["x", "y", "z"][:dimensions]
        return SpatialTrajDisplay(
            traj_name=base_name,
            traj_dims=dimensions,
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
    dimensions: int,
) -> PyViewConfig:
    first_variable = next(iter(data.values()))

    comps = args.get("comps")
    # Assume it's somewhat valid, because if it's not, the error should have
    # happened earlier when loading trajectories
    if np.isscalar(comps):
        comps = list(range(comps))

    palate_variable = args.get("palate")
    palate_trace = None
    if palate_variable is not None:
        palate_trace = other_data[palate_variable]
        if palate_trace.ndim != 2 or palate_trace.shape[1] < 2:
            raise ValueError(
                f"Palate trace variable '{palate_variable}' must be a 2D array with at least 2 columns for spatial data, but has shape {palate_trace.shape}"
            )
        if comps is not None:
            if max(comps) >= palate_trace.shape[1]:
                raise ValueError(
                    f"--comps {comps} is invalid for palate trace with shape {palate_trace.shape}"
                )
            palate_trace = palate_trace[:, comps]
        elif palate_trace.shape[1] > dimensions:
            palate_trace = palate_trace[:, :dimensions]
        del other_data[palate_variable]

    spline_trajs = args.get("spline")
    if spline_trajs is None:
        spline_trajs = [
            name
            for name, val in first_variable.trajectories.items()
            if name.startswith("T") and val.kind == "spatial"
        ]
    else:
        spline_trajs = [normalize_traj_name(name) for name in spline_trajs]
        for name in spline_trajs:
            for variable in data.values():
                if name not in variable.trajectories:
                    raise ValueError(
                        f"Spline trajectory '{name}' not found in variable '{variable.name}'"
                    )
                if variable.trajectories[name].kind != "spatial":
                    raise ValueError(
                        f"Spline trajectory '{name}' found in variable '{variable.name}' but is not spatial"
                    )

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
        audio_traj = normalize_traj_name(audio_traj)
        if audio_traj not in first_variable.trajectories:
            raise ValueError(
                f"Audio trajectory '{audio_traj}' not found among trajectories of variable '{first_variable.name}'"
            )
        if first_variable.trajectories[audio_traj].kind != "scalar":
            raise ValueError(f"Audio trajectory '{audio_traj}' found but is not scalar")

    framing_traj = args.get("framing", audio_traj)
    if framing_traj is None:
        framing_traj = next(iter(first_variable.trajectories.keys()))
    else:
        framing_traj = normalize_traj_name(framing_traj)
        if framing_traj not in first_variable.trajectories:
            raise ValueError(
                f"Framing trajectory '{framing_traj}' not found among trajectories of variable '{first_variable.name}'"
            )

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
        parse_trajectory_display_spec(name, first_variable, dimensions)
        for name in temporal_disp_trajs
    ]

    return PyViewConfig(
        palate_trace=palate_trace,
        spline_trajs=spline_trajs,
        audio_traj=audio_traj,
        framing_traj=framing_traj,
        temporal_disp_specs=temporal_disp_specs,
    )
