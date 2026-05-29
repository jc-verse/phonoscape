from pathlib import Path
from fnmatch import fnmatch

import numpy as np
import matplotlib.pyplot as plt
from scipy.io import loadmat

from .state import DatasetVariable, Trajectory


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
                color=plt.rcParams["text.color"] if kind == "scalar" else next(colors_iter),
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
