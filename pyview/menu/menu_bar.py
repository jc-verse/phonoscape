from typing import TYPE_CHECKING

import tkinter as tk

from .play_menu import PlayMenu
from .selection_menu import SelectionMenu
from .view_menu import ViewMenu

if TYPE_CHECKING:
    from .. import PyViewTk
from ..data.process import get_plotting_data
from ..state import PyViewState, ScalarTrajDisplay


class MenuBar(tk.Menu):
    def __init__(self, parent: PyViewTk, state_model: PyViewState) -> None:
        super().__init__(parent)
        self.parent = parent
        self.state_model = state_model

        file_menu = tk.Menu(self, tearoff=False)
        variables_menu = tk.Menu(file_menu, tearoff=False)
        for name in self.state_model.variable_names:
            variables_menu.add_radiobutton(
                label=name,
                variable=parent.selected_variable_var,
                value=name,
                command=self._on_variable_change,
            )
        file_menu.add_cascade(label="Variables", menu=variables_menu)
        file_menu.add_separator()
        save_menu = tk.Menu(file_menu, tearoff=False)
        save_menu.add_command(
            label="Save all but selection...",
            command=self._todo("Save all but selection"),
        )
        save_menu.add_command(
            label="Save selection only...", command=self._todo("Save selection only")
        )
        file_menu.add_cascade(label="Save", menu=save_menu)
        file_menu.add_command(label="Export...", command=self._todo("Export"))
        file_menu.add_command(label="Close window", command=self._todo("Close window"))
        file_menu.add_command(label="Close all", command=self._todo("Close all"))
        self.add_cascade(label="File", menu=file_menu)

        data_menu = tk.Menu(self, tearoff=False)
        data_menu.add_command(label="Report", command=self._todo("Report"))
        data_menu.add_command(
            label="Track formants", command=self._todo("Track formants")
        )
        data_menu.add_command(
            label="Spectral analysis...", command=self._todo("Spectral analysis")
        )
        self.add_cascade(label="Data", menu=data_menu)

        self.add_cascade(label="View", menu=ViewMenu(self, self.state_model))
        self.add_cascade(label="Selection", menu=SelectionMenu(self, self.state_model))
        self.add_cascade(label="Play", menu=PlayMenu(self, self.state_model))

        movement_menu = tk.Menu(self, tearoff=False)
        movement_menu.add_command(
            label="Step forward", command=self._todo("Step forward")
        )
        movement_menu.add_command(
            label="Step backward", command=self._todo("Step backward")
        )
        movement_menu.add_command(
            label="Shift forward", command=self._todo("Shift forward")
        )
        movement_menu.add_command(
            label="Shift backward", command=self._todo("Shift backward")
        )
        movement_menu.add_separator()
        movement_menu.add_command(
            label="Reflective cycling", command=self._todo("Reflective cycling")
        )
        movement_menu.add_command(
            label="Cycle forward", command=self._todo("Cycle forward")
        )
        movement_menu.add_command(
            label="Cycle backward", command=self._todo("Cycle backward")
        )
        movement_menu.add_command(
            label="Stop cycling", command=self._todo("Stop cycling")
        )
        self.add_cascade(label="Movement", menu=movement_menu)

        label_menu = tk.Menu(self, tearoff=False)
        label_menu.add_command(
            label="Make label...", command=self._todo("Make label...")
        )
        label_menu.add_command(
            label="Edit labels...", command=self._todo("Edit labels...")
        )
        label_menu.add_command(
            label="Clear all labels", command=self._todo("Clear all labels")
        )
        label_menu.add_separator()
        label_menu.add_command(
            label="Export labels...", command=self._todo("Export labels...")
        )
        label_menu.add_command(
            label="Import labels...", command=self._todo("Import labels...")
        )
        label_menu.add_separator()
        label_menu.add_command(
            label="Save labels...", command=self._todo("Save labels...")
        )
        label_menu.add_command(
            label="Load labels...", command=self._todo("Load labels...")
        )
        label_menu.add_command(
            label="Set selection to label pair",
            command=self._todo("Set selection to label pair"),
        )
        labeling_behavior_menu = tk.Menu(label_menu, tearoff=False)
        labeling_behavior_menu.add_command(label="Clear", command=self._todo("Clear"))
        labeling_behavior_menu.add_command(
            label="Select...", command=self._todo("Select...")
        )
        labeling_behavior_menu.add_command(
            label="Configure...", command=self._todo("Configure...")
        )
        label_menu.add_cascade(label="Labeling behavior", menu=labeling_behavior_menu)
        self.add_cascade(label="Labels", menu=label_menu)

    def _on_variable_change(self) -> None:
        name = self.parent.selected_variable_var.get()
        self.state_model.selected_variable = name
        self.parent.info_label.config(
            text=f"{name} ({self.state_model.data[name].duration_s:.2f}s)"
        )
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
        self.state_model.head_s = min(
            self.state_model.head_s,
            max(
                0,
                self.state_model.data[name].duration_s - self.state_model.min_sel_dur_s,
            ),
        )
        self.state_model.tail_s = min(
            self.state_model.tail_s, self.state_model.data[name].duration_s
        )
        self.parent.temporal_view.update_plot(cursor=True, variable=True)
        if self.state_model.audio_spect is not None:
            self.parent.freq_domain_view.update_plot()
        self.parent.spatial_view.update_plot(points=True)

    def _todo(self, action: str):
        return lambda: print(f"TODO: {action}")
