import sys
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import cast, Literal, Unpack
import matplotlib.pyplot as plt

from .data.parse import load_variables, normalize_args, PyViewArgs
from .data.process import get_plotting_data
from .menu.menu_bar import MenuBar
from .state import PyViewState, ScalarTrajDisplay
from .widgets.play_button import PlayButton, modes as play_modes
from .views.temporal_view import TemporalView
from .views.spatial_view_3d import SpatialView3D
from .views.spatial_view_2d import SpatialView2D
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
        # Listbox still uses Control-click for toggling on mac. Swap it to Command-click
        if sys.platform == "darwin" and (
            ctrl_script := self.bind_class("Listbox", "<Control-Button-1>")
        ):
            self.bind_class("Listbox", "<Command-Button-1>", ctrl_script)
            self.bind_class("Listbox", "<Control-Button-1>", "")

        path = Path(file)
        data, other_data, dimensions = load_variables(
            path, variables, comps=kwargs.get("comps")
        )

        if not data:
            raise ValueError(f"No matching variables found for pattern {variables!r}")

        config = normalize_args(kwargs, data, other_data, dimensions)

        min_x, min_y, min_z = float("inf"), float("inf"), float("inf")
        max_x, max_y, max_z = float("-inf"), float("-inf"), float("-inf")
        for variable in data.values():
            for traj in variable.trajectories.values():
                if traj.kind != "spatial":
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
        if config.palate_trace is not None:
            palate_trace = config.palate_trace
            if dimensions == 3:
                x, y, z = palate_trace.T
                min_x, max_x = min(min_x, x.min()), max(max_x, x.max())
                min_y, max_y = min(min_y, y.min()), max(max_y, y.max())
                min_z, max_z = min(min_z, z.min()), max(max_z, z.max())
            else:
                x, y = palate_trace.T
                min_x, max_x = min(min_x, x.min()), max(max_x, x.max())
                min_y, max_y = min(min_y, y.min()), max(max_y, y.max())

        selected_variable = next(iter(data.keys()))

        self.state_model = PyViewState(
            file=path,
            variables_pattern=variables,
            data=data,
            other_data=other_data,
            labels=[],
            audio_spect=(
                get_plotting_data(
                    data[selected_variable].trajectories[config.audio_traj],
                    ScalarTrajDisplay(traj_name=config.audio_traj, content="SPECT"),
                    dimensions,
                )
                if config.audio_traj is not None
                else None
            ),
            selected_variable=selected_variable,
            dpi=self.winfo_fpixels("1i"),
            dimensions=cast(Literal[2, 3], dimensions),
            spatial_bounds=(
                (min_x, max_x, min_y, max_y, min_z, max_z)
                if dimensions == 3
                else (min_x, max_x, min_y, max_y)
            ),
            config=config,
            cursor_s=0.0,
            head_s=0.0,
            tail_s=data[selected_variable].duration_s,
            play_mode=tk.StringVar(value=play_modes[0]),
        )

        self.title(f"PyView - {path.name}")
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
            play_button = PlayButton(navbar, self.state_model)
            play_button.grid(row=0, column=0, sticky="w", padx=(0, 12))

        self.info_label = ttk.Label(
            navbar,
            text=f"{self.state_model.selected_variable} ({self.state_model.data[self.state_model.selected_variable].duration_s:.2f}s)",
        )
        self.info_label.grid(row=0, column=1, sticky="w")

        left = ttk.Frame(self)
        left.grid(row=1, column=0, sticky="nsew", padx=(4, 2), pady=(0, 4))
        left.rowconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        if self.state_model.dimensions == 3:
            self.spatial_view = SpatialView3D(left, state_model=self.state_model)
        else:
            self.spatial_view = SpatialView2D(left, state_model=self.state_model)
        self.spatial_view.grid(row=0, column=0, sticky="nsew")

        self.freq_domain_view = FreqDomainView(left, state_model=self.state_model)
        self.freq_domain_view.grid(row=1, column=0, sticky="nsew")

        right = ttk.Frame(self)
        right.grid(row=1, column=1, sticky="nsew", padx=(2, 4), pady=(0, 4))
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        self.temporal_view = TemporalView(
            right,
            state_model=self.state_model,
            on_cursor_change=self._on_cursor_change,
        )
        self.temporal_view.grid(row=0, column=0, sticky="nsew")

        # Important: create menu bar after views, because it directly manipulates them
        self.selected_variable_var = tk.StringVar(
            value=self.state_model.selected_variable
        )
        self.menu_bar = MenuBar(self, self.state_model)
        self.config(menu=self.menu_bar)

    def _on_cursor_change(self) -> None:
        self.spatial_view.update_plot(points=True)
        if self.state_model.config.audio_traj is not None:
            self.freq_domain_view.update_plot()


def pyview(file: str, variables: str = "*", **kwargs: Unpack[PyViewArgs]) -> None:
    app = PyViewTk(file, variables, **kwargs)
    app.mainloop()
