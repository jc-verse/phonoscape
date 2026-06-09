import sys
from pathlib import Path
from typing import Unpack
from PySide6.QtWidgets import QApplication
import matplotlib.pyplot as plt

from .data.parse import load_variables, normalize_args, PyViewArgs
from .window import PyViewWindow, WindowManager


def pyview(file: str, variables: str = "*", **kwargs: Unpack[PyViewArgs]) -> None:
    plt.style.use("dark_background")

    path = Path(file)
    data, other_data, dimensions = load_variables(
        path, variables, comps=kwargs.get("comps")
    )

    if not data:
        raise ValueError(f"No matching variables found for pattern {variables!r}")

    app_config, temporal_disp_specs = normalize_args(
        path, kwargs, data, other_data, dimensions
    )

    selected_variable = next(iter(data.keys()))

    head_s = (kwargs.get("head") or 0) / 1000
    tail_s = (kwargs.get("tail") or data[selected_variable].duration_s * 1000) / 1000
    tail_s = min(tail_s, data[selected_variable].duration_s)
    if head_s < 0:
        raise ValueError(
            f"--head must be a non-negative number of milliseconds, but got {head_s * 1000}"
        )
    if tail_s < 0:
        raise ValueError(
            f"--tail must be a non-negative number of milliseconds, but got {tail_s * 1000}"
        )
    if head_s >= tail_s:
        raise ValueError(
            f"--head must be less than --tail, but got head={head_s * 1000} and tail={tail_s * 1000}"
        )
    elif tail_s - head_s < 0.025:
        raise ValueError(
            f"The duration of the selection (tail - head) must be at least 25 milliseconds, but got head={head_s * 1000} and tail={tail_s * 1000} ({(tail_s - head_s) * 1000:.1f} ms)"
        )

    app = QApplication.instance()
    owns_app = app is None

    if app is None:
        app = QApplication(sys.argv)

    window_manager = WindowManager()
    window = PyViewWindow(
        window_manager=window_manager,
        selected_variable=selected_variable,
        dimensions=dimensions,
        temporal_disp_specs=temporal_disp_specs,
        app_config=app_config,
        head_s=head_s,
        tail_s=tail_s,
    )
    window.show()

    if owns_app:
        sys.exit(app.exec())
