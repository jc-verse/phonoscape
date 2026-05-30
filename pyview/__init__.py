import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Unpack
import matplotlib.pyplot as plt

from .data.parse import load_variables, normalize_args, PyViewArgs
from .data.process import get_plotting_data
from .state import PyViewState, ScalarTrajDisplay
from .widgets.play_button import SplitPlayButton
from .widgets.variable_dropdown import VariableDropdown
from .views.temporal_view import TemporalView
from .views.spatial_view import SpatialView
from .views.freq_domain_view import FreqDomainView


class PyViewTk(tk.Tk):
    def __init__(
        self,
        file: str | Path,
        variables: str = "*",
        **kwargs: Unpack[PyViewArgs],
    ):
        super().__init__()
        plt.style.use("dark_background")

        path = Path(file)
        data, other_data = load_variables(path, variables)

        if not data:
            raise ValueError(f"No matching variables found for pattern {variables!r}")

        config = normalize_args(kwargs, data, other_data)

        min_x, min_y, min_z = float("inf"), float("inf"), float("inf")
        max_x, max_y, max_z = float("-inf"), float("-inf"), float("-inf")
        for variable in data.values():
            for traj in variable.trajectories.values():
                if traj.kind != "spatial":
                    continue
                x, y, z = traj.data[:, :3].T
                min_x, max_x = min(min_x, x.min()), max(max_x, x.max())
                min_y, max_y = min(min_y, y.min()), max(max_y, y.max())
                min_z, max_z = min(min_z, z.min()), max(max_z, z.max())
        if config.palate_trace is not None:
            palate_trace = config.palate_trace
            x, y, z = palate_trace[:, :3].T
            min_x, max_x = min(min_x, x.min()), max(max_x, x.max())
            min_y, max_y = min(min_y, y.min()), max(max_y, y.max())
            min_z, max_z = min(min_z, z.min()), max(max_z, z.max())

        selected_variable = next(iter(data.keys()))

        self.state_model = PyViewState(
            file=path,
            variables_pattern=variables,
            data=data,
            other_data=other_data,
            audio_spect=(
                get_plotting_data(
                    data[selected_variable].trajectories[config.audio_traj],
                    ScalarTrajDisplay(traj_name=config.audio_traj, content="SPECT"),
                )
                if config.audio_traj is not None
                else None
            ),
            selected_variable=selected_variable,
            dpi=self.winfo_fpixels("1i"),
            spatial_bounds=(min_x, max_x, min_y, max_y, min_z, max_z),
            config=config,
            cursor_s=0.0,
        )

        self.title(f"pyview - {path.name}")
        self.geometry("1440x1000")

        self._build_ui()

    def _build_ui(self) -> None:
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)

        navbar = ttk.Frame(self)
        navbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=6)
        navbar.columnconfigure(3, weight=1)

        if self.state_model.config.audio_traj is not None:
            play_button = SplitPlayButton(navbar, self.state_model)
            play_button.grid(row=0, column=0, sticky="w", padx=(0, 12))

        self.variable_box = VariableDropdown(
            navbar,
            variable_names=self.state_model.variable_names,
            on_variable_changed=self._on_variable_change,
        )
        self.variable_box.grid(row=0, column=2, sticky="ew", padx=(6, 12))

        left = ttk.Frame(self)
        left.grid(row=1, column=0, sticky="nsew", padx=(4, 2), pady=(0, 4))
        left.rowconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        self.spatial_view = SpatialView(left, state_model=self.state_model)
        self.spatial_view.grid(row=0, column=0, sticky="nsew")
        self.spatial_view.reset_plot()

        self.freq_domain_view = FreqDomainView(left, state_model=self.state_model)
        self.freq_domain_view.grid(row=1, column=0, sticky="nsew")
        if self.state_model.audio_spect is not None:
            self.freq_domain_view.reset_plot()

        right = ttk.Frame(self)
        right.grid(row=1, column=1, sticky="nsew", padx=(2, 4), pady=(0, 4))
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        self.temporal_view = TemporalView(
            right,
            state_model=self.state_model,
            on_cursor_changed=self._on_cursor_changed,
        )
        self.temporal_view.grid(row=0, column=0, sticky="nsew")
        self.temporal_view.reset_plot()

    def _on_variable_change(self, name: str) -> None:
        self.state_model.selected_variable = name
        self.state_model.cursor_s = 0.0
        self.state_model.audio_spect = (
            get_plotting_data(
                self.state_model.data[name].trajectories[
                    self.state_model.config.audio_traj
                ],
                ScalarTrajDisplay(
                    traj_name=self.state_model.config.audio_traj, content="SPECT"
                ),
            )
            if self.state_model.config.audio_traj is not None
            else None
        )
        self.temporal_view.update_plot(cursor=True, variable=True)
        if self.state_model.audio_spect is not None:
            self.freq_domain_view.update_plot()
        self.spatial_view.update_plot(points=True)

    def _on_cursor_changed(self) -> None:
        self.spatial_view.update_plot(points=True)
        if self.state_model.config.audio_traj is not None:
            self.freq_domain_view.update_plot()


def pyview(file: str, variables: str = "*", **kwargs: Unpack[PyViewArgs]) -> None:
    app = PyViewTk(file, variables, **kwargs)
    app.mainloop()
