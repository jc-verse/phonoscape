from pathlib import Path
import re
from fnmatch import fnmatch
from typing import TypedDict, Literal, cast, Any

import numpy as np
import matplotlib.pyplot as plt
from scipy.io import loadmat

from ..state import (
    DatasetVariable,
    Trajectory,
    TrajDisplay,
    AudioTrajDisplay,
    ScalarTrajDisplay,
    SpatialTrajDisplay,
    Color,
    AppConfig,
    get_component_names,
)


class CmdArgs(TypedDict, total=False):
    palate: str | None
    pharynx: str | None
    spline: list[str] | None
    polyline_spline: bool | None
    audio: str | None
    framing: str | None
    temporal_display: list[str] | None
    spatial_exclude: list[str] | None
    comps: int | list[int] | None
    view: tuple[float, float, float] | None
    head: float | None
    tail: float | None
    sex: Literal["M", "F"] | None
    spect_lim: float | None


def get_optional(arr: np.ndarray, name: str) -> np.ndarray | list[None]:
    if arr.dtype.names and name in arr.dtype.names:
        return arr[name]
    else:
        return [None] * len(arr)


def normalize_traj_name(name: str) -> str:
    return str(name).strip().upper().replace("_", "")


def is_data(arr: np.ndarray) -> bool:
    return (
        arr.dtype.names is not None
        and "NAME" in arr.dtype.names
        and "SRATE" in arr.dtype.names
        and "SIGNAL" in arr.dtype.names
    )


def load_variables(
    file: str | Path, variables_pattern: str, comps: int | list[int] | None
) -> tuple[dict[str, DatasetVariable], dict[str, Any], Literal[2, 3]]:
    raw = loadmat(file, squeeze_me=True)

    raw = {k: v for k, v in raw.items() if not k.startswith("__")}
    data = {k: v for k, v in raw.items() if is_data(v)}
    other = {k: v for k, v in raw.items() if not is_data(v)}

    if variables_pattern != "*":
        data = {k: v for k, v in data.items() if fnmatch(k, variables_pattern)}

    structured_data: dict[str, DatasetVariable] = {}
    seen_dimensions = set()
    for k, v in data.items():
        trajectories: dict[str, Trajectory] = {}
        estimated_durations = []
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
            kind = (
                "spatial" if signal.ndim == 2 else "scalar" if srate < 5000 else "audio"
            )
            if nComps is None:
                nComps = comps or (
                    list(range(max(3, signal.shape[1]))) if signal.ndim == 2 else [0]
                )
            if np.isscalar(nComps):
                nComps = list(range(int(nComps)))
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
                    color
                    if isinstance(color, str)
                    else tuple(color) if color is not None else None
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
            # Added later because we only know the default audio traj *after* loading
            audio_traj=None,
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
    name: str, first_variable: DatasetVariable, dimensions: Literal[2, 3]
) -> TrajDisplay:
    if match := re.match(r"^(.*)_(SPECT|RMS|ZC|F0)$", name):
        base_name, content = match.groups()
        if (
            base_name in first_variable.trajectories
            and first_variable.trajectories[base_name].kind == "audio"
        ):
            return AudioTrajDisplay(
                traj_name=base_name,
                content=cast(Literal["SPECT", "RMS", "ZC", "F0"], content),
            )
        else:
            raise ValueError(
                f"Trajectory '{name}' does not match any known audio trajectory for variable '{first_variable.name}'{f" (but this trajectory exists as {first_variable.trajectories[base_name].kind} trajectory)" if base_name in first_variable.trajectories else ''}"
            )
    if match := re.match(r"^(.*)_(VEL|ABSVEL)$", name):
        base_name, content = match.groups()
        if (
            base_name in first_variable.trajectories
            and first_variable.trajectories[base_name].kind == "scalar"
        ):
            return ScalarTrajDisplay(
                traj_name=base_name, content=cast(Literal["VEL", "ABSVEL"], content)
            )
        else:
            raise ValueError(
                f"Trajectory '{name}' does not match any known scalar trajectory for variable '{first_variable.name}'{f" (but this trajectory exists as {first_variable.trajectories[base_name].kind} trajectory)" if base_name in first_variable.trajectories else ''}"
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
            components = get_component_names(dimensions)
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
    elif base_name in first_variable.trajectories and first_variable.trajectories[
        base_name
    ].kind in ("scalar", "audio"):
        if content or x or y or z:
            raise ValueError(
                f"Trajectory '{base_name}' is {first_variable.trajectories[base_name].kind}"
            )
        if first_variable.trajectories[base_name].kind == "audio":
            return AudioTrajDisplay(traj_name=base_name, content="SIGNAL")
        else:
            return ScalarTrajDisplay(traj_name=base_name, content="MOVEMENT")
    else:
        raise ValueError(
            f"Trajectory '{name}' does not match any known trajectory for variable '{first_variable.name}'{f" (but this trajectory exists as {first_variable.trajectories[base_name].kind} trajectory)" if base_name in first_variable.trajectories else ''}"
        )


def normalize_args(
    file: Path,
    args: CmdArgs,
    data: dict[str, DatasetVariable],
    other_data: dict[str, Any],
    dimensions: Literal[2, 3],
):
    first_variable = next(iter(data.values()))

    comps = args.get("comps")
    # Assume it's somewhat valid, because if it's not, the error should have
    # happened earlier when loading trajectories
    if np.isscalar(comps):
        comps = list(range(comps))

    palate_variable = args.get("palate")
    palate_trace = None
    if (
        palate_variable is None
        and "pal" in other_data
        and isinstance(other_data["pal"], np.ndarray)
        and other_data["pal"].ndim == 2
        and other_data["pal"].shape[1] >= 2
    ):
        palate_variable = "pal"
    if palate_variable is not None:
        palate_trace = other_data[palate_variable]
        if not isinstance(palate_trace, np.ndarray):
            raise ValueError(
                f"Palate trace variable '{palate_variable}' found but is not a numpy array"
            )
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

    pharynx_variable = args.get("pharynx")
    pharynx_trace = None
    if (
        pharynx_variable is None
        and "pha" in other_data
        and isinstance(other_data["pha"], np.ndarray)
        and other_data["pha"].ndim == 2
        and other_data["pha"].shape[1] >= 2
    ):
        pharynx_variable = "pha"
    if pharynx_variable is not None:
        pharynx_trace = other_data[pharynx_variable]
        if not isinstance(pharynx_trace, np.ndarray):
            raise ValueError(
                f"Pharynx trace variable '{pharynx_variable}' found but is not a numpy array"
            )
        if pharynx_trace.ndim != 2 or pharynx_trace.shape[1] < 2:
            raise ValueError(
                f"Pharynx trace variable '{pharynx_variable}' must be a 2D array with at least 2 columns for spatial data, but has shape {pharynx_trace.shape}"
            )
        if pharynx_trace.shape[1] == 2 and dimensions == 3:
            # If only 2 columns, assume it's x/z and add a dummy y column of zeros for easier handling downstream
            # This is consistent with MVIEW, which requires pharynx traces to be 2D
            # TODO: should the extra column be y or z or customizable?
            pharynx_trace = np.hstack(
                [
                    pharynx_trace[:, 0:1],
                    np.zeros((pharynx_trace.shape[0], 1)),
                    pharynx_trace[:, 1:2],
                ]
            )
            print(
                "Your pharynx trace is 2D but your spatial data is 3D. This is allowed by MVIEW and an extra y column of zeros has been added, but editing your data to be 3D is recommended."
            )
        if comps is not None:
            if max(comps) >= pharynx_trace.shape[1]:
                raise ValueError(
                    f"--comps {comps} is invalid for pharynx trace with shape {pharynx_trace.shape}"
                )
            pharynx_trace = pharynx_trace[:, comps]
        elif pharynx_trace.shape[1] > dimensions:
            pharynx_trace = pharynx_trace[:, :dimensions]
        del other_data[pharynx_variable]

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
                if traj.kind == "audio"
            ),
            None,
        )
    else:
        audio_traj = normalize_traj_name(audio_traj)
        if audio_traj not in first_variable.trajectories:
            raise ValueError(
                f"Audio trajectory '{audio_traj}' not found among trajectories of variable '{first_variable.name}'"
            )
        if first_variable.trajectories[audio_traj].kind != "audio":
            raise ValueError(f"Audio trajectory '{audio_traj}' found but is not audio")

    framing_traj = args.get("framing", audio_traj)
    if framing_traj is None:
        framing_traj = next(iter(first_variable.trajectories.keys()))
    else:
        framing_traj = normalize_traj_name(framing_traj)
        if framing_traj not in first_variable.trajectories:
            raise ValueError(
                f"Framing trajectory '{framing_traj}' not found among trajectories of variable '{first_variable.name}'"
            )

    temporal_display = args.get("temporal_display")
    if temporal_display is None:
        temporal_display = list(first_variable.trajectories.keys())
        if audio_traj:
            temporal_display.remove(audio_traj)
            temporal_display = [
                audio_traj,
                f"{audio_traj}_SPECT",
            ] + temporal_display
    temporal_disp_specs = [
        parse_trajectory_display_spec(name, first_variable, dimensions)
        for name in temporal_display
    ]

    spatial_exclude = args.get("spatial_exclude") or []
    spatial_exclude = [normalize_traj_name(name) for name in spatial_exclude]
    for name in spatial_exclude:
        found = False
        for variable in data.values():
            if name in variable.trajectories:
                traj = variable.trajectories[name]
                if traj.kind == "spatial":
                    found = True
                    break
                else:
                    raise ValueError(
                        f"Trajectory '{name}' specified for exclusion from spatial view, but it is not a spatial trajectory (found as {traj.kind} trajectory in variable '{variable.name}')"
                    )
        if not found:
            raise ValueError(
                f"Trajectory '{name}' specified for exclusion from spatial view was not found in any variable"
            )

    min_x, min_y, min_z = float("inf"), float("inf"), float("inf")
    max_x, max_y, max_z = float("-inf"), float("-inf"), float("-inf")
    for variable in data.values():
        for traj in variable.trajectories.values():
            if traj.kind != "spatial" or traj.name in spatial_exclude:
                continue
            if dimensions == 3:
                x, y, z = traj.data.T
                min_x, max_x = min(min_x, x.min()), max(max_x, x.max())
                min_y, max_y = min(min_y, y.min()), max(max_y, y.max())
                min_z, max_z = min(min_z, z.min()), max(max_z, z.max())
            else:
                x, y = traj.data.T
                min_x, max_x = min(min_x, x.min()), max(max_x, x.max())
                min_y, max_y = min(min_y, y.min()), max(max_y, y.max())
    if palate_trace is not None:
        if dimensions == 3:
            x, y, z = palate_trace.T
            min_x, max_x = min(min_x, x.min()), max(max_x, x.max())
            min_y, max_y = min(min_y, y.min()), max(max_y, y.max())
            min_z, max_z = min(min_z, z.min()), max(max_z, z.max())
        else:
            x, y = palate_trace.T
            min_x, max_x = min(min_x, x.min()), max(max_x, x.max())
            min_y, max_y = min(min_y, y.min()), max(max_y, y.max())

    config = AppConfig(
        file=file,
        data=data,
        other_data=other_data,
        palate_trace=palate_trace,
        pharynx_trace=pharynx_trace,
        spline_trajs=spline_trajs,
        polyline_spline=args.get("polyline_spline") or False,
        audio_traj=audio_traj,
        framing_traj=framing_traj,
        spatial_bounds=(
            (min_x, max_x, min_y, max_y, min_z, max_z)
            if dimensions == 3
            else (min_x, max_x, min_y, max_y)
        ),
        spatial_exclude=spatial_exclude,
        dimensions=dimensions,
        is_female=(args.get("sex") == "F"),
        spectral_display_cutoff_hz=args.get("spect_lim") or 11025.0,
    )

    if audio_traj is not None:
        audio_sr = first_variable.trajectories[audio_traj].sample_rate_hz
        # Consistent with MVIEW
        config.lpc_order = round(audio_sr / 1000) + (8 if config.is_female else 4)
        config.spectral_display_cutoff_hz = args.get("spect_lim") or (audio_sr / 2)

    prop_cycle = plt.rcParams["axes.prop_cycle"]
    colors = prop_cycle.by_key()["color"]
    colors_iter = iter(colors)
    colors: dict[str, Color] = {}
    for name, traj in first_variable.trajectories.items():
        colors[name] = traj.color or (
            plt.rcParams["text.color"]
            if traj.kind == "scalar" or traj.kind == "audio"
            else next(colors_iter)
        )

    return config, temporal_disp_specs, colors
