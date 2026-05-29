import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import TypedDict, Unpack
import matplotlib.pyplot as plt

from .data import load_variables
from .state import PyViewState
from .widgets.play_button import SplitPlayButton
from .widgets.variable_dropdown import VariableDropdown
from .views.temporal_view import TemporalView
from .views.spatial_view import SpatialView


class PyViewArgs(TypedDict, total=False):
    palate: str | None
    spline: list[str] | None
    audio: str | None
    framing: str | None
    temporal_map: list[str] | None


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

        first_variable = next(iter(data))
        audio_traj = kwargs.get("audio")
        if audio_traj is None:
            audio_traj = next(
                (
                    name
                    for name, traj in data[first_variable].trajectories.items()
                    if traj.sample_rate_hz > 1000 and traj.kind == "scalar"
                ),
                None,
            )

        temporal_map = kwargs.get("temporal_map")
        if temporal_map is None:
            temporal_map = list(data[first_variable].trajectories.keys())
            if audio_traj:
                temporal_map.remove(audio_traj)
                temporal_map = [audio_traj, f"{audio_traj}_spect"] + temporal_map

        self.state_model = PyViewState(
            file=path,
            variables_pattern=variables,
            data=data,
            other_data=other_data,
            selected_variable=first_variable,
            temporal_map=temporal_map,
            dpi=self.winfo_fpixels("1i"),
            palate_variable=kwargs.get("palate"),
            spline_trajs=kwargs.get("spline"),
            audio_traj=audio_traj,
            framing_traj=kwargs.get("framing", audio_traj),
        )

        self.title(f"pyview - {path.name}")
        self.geometry("1440x1000")

        self._build_ui()
        self.plot()

    def _build_ui(self) -> None:
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)

        navbar = ttk.Frame(self)
        navbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=6)
        navbar.columnconfigure(3, weight=1)

        play_button = SplitPlayButton(navbar, on_play=self._play_current_mode)
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

    def _on_variable_change(self, name: str) -> None:
        self.state_model.selected_variable = name
        self.state_model.cursor_s = 0.0
        self.plot()

    def _on_cursor_changed(self, t: float) -> None:
        self.state_model.cursor_s = t
        self.spatial_view.plot()

    def plot(self) -> None:
        self.temporal_view.plot()
        self.spatial_view.plot()

    def _play_current_mode(self, mode: str) -> None:
        print(f"Play mode: {mode}")  # TODO


def pyview(file: str, variables: str = "*", **kwargs: Unpack[PyViewArgs]) -> None:
    app = PyViewTk(file, variables, **kwargs)
    app.mainloop()
