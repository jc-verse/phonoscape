from typing import TYPE_CHECKING

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu, QMenuBar

from .play_menu import PlayMenu
from .selection_menu import SelectionMenu
from .view_menu import ViewMenu

if TYPE_CHECKING:
    from .. import PyViewQt

from ..data.process import get_plotting_data
from ..state import PyViewState, ScalarTrajDisplay


class MenuBar(QMenuBar):
    def __init__(self, parent: PyViewQt, state_model: PyViewState) -> None:
        super().__init__(parent)

        self.root = parent
        self.state_model = state_model

        file_menu = QMenu("File", self)

        variables_menu = QMenu("Variables", file_menu)
        self.variable_action_group = QActionGroup(self)
        self.variable_action_group.setExclusive(True)

        current_variable = parent.selected_variable_var.get()

        for name in self.state_model.variable_names:
            action = QAction(name, self)
            action.setCheckable(True)
            action.setChecked(name == current_variable)
            action.triggered.connect(
                lambda checked=False, name=name: self._on_variable_change(name)
            )

            self.variable_action_group.addAction(action)
            variables_menu.addAction(action)

        file_menu.addMenu(variables_menu)
        file_menu.addSeparator()

        save_menu = QMenu("Save", file_menu)
        save_menu.addAction(
            "Save all but selection...",
            self._todo("Save all but selection"),
        )
        save_menu.addAction(
            "Save selection only...",
            self._todo("Save selection only"),
        )

        file_menu.addMenu(save_menu)
        file_menu.addAction("Export...", self._todo("Export"))
        file_menu.addAction("Close window", self._todo("Close window"))
        file_menu.addAction("Close all", self._todo("Close all"))
        self.addMenu(file_menu)

        data_menu = QMenu("Data", self)
        data_menu.addAction("Report", self._todo("Report"))
        data_menu.addAction("Track formants", self._todo("Track formants"))
        data_menu.addAction("Spectral analysis...", self._todo("Spectral analysis"))
        self.addMenu(data_menu)

        self.addMenu(ViewMenu(self, self.state_model))
        self.addMenu(SelectionMenu(self, self.state_model))
        self.addMenu(PlayMenu(self, self.state_model))

        movement_menu = QMenu("Movement", self)
        movement_menu.addAction("Step forward", self._todo("Step forward"))
        movement_menu.addAction("Step backward", self._todo("Step backward"))
        movement_menu.addAction("Shift forward", self._todo("Shift forward"))
        movement_menu.addAction("Shift backward", self._todo("Shift backward"))
        movement_menu.addSeparator()
        movement_menu.addAction("Reflective cycling", self._todo("Reflective cycling"))
        movement_menu.addAction("Cycle forward", self._todo("Cycle forward"))
        movement_menu.addAction("Cycle backward", self._todo("Cycle backward"))
        movement_menu.addAction("Stop cycling", self._todo("Stop cycling"))
        self.addMenu(movement_menu)

        label_menu = QMenu("Labels", self)
        label_menu.addAction("Make label...", self._todo("Make label..."))
        label_menu.addAction("Edit labels...", self._todo("Edit labels..."))
        label_menu.addAction("Clear all labels", self._todo("Clear all labels"))
        label_menu.addSeparator()
        label_menu.addAction("Export labels...", self._todo("Export labels..."))
        label_menu.addAction("Import labels...", self._todo("Import labels..."))
        label_menu.addSeparator()
        label_menu.addAction("Save labels...", self._todo("Save labels..."))
        label_menu.addAction("Load labels...", self._todo("Load labels..."))
        label_menu.addAction(
            "Set selection to label pair",
            self._todo("Set selection to label pair"),
        )

        labeling_behavior_menu = QMenu("Labeling behavior", label_menu)
        labeling_behavior_menu.addAction("Clear", self._todo("Clear"))
        labeling_behavior_menu.addAction("Select...", self._todo("Select..."))
        labeling_behavior_menu.addAction("Configure...", self._todo("Configure..."))

        label_menu.addMenu(labeling_behavior_menu)
        self.addMenu(label_menu)

    def _on_variable_change(self, name: str) -> None:
        self.root.selected_variable_var.set(name)
        self.state_model.selected_variable = name

        self.root.info_label.setText(
            f"{name} ({self.state_model.data[name].duration_s:.2f}s)"
        )
        self.state_model.cursor_s = 0.0
        self.state_model.audio_spect = (
            get_plotting_data(
                self.state_model.data[name].trajectories[
                    self.state_model.config.audio_traj
                ],
                ScalarTrajDisplay(
                    traj_name=self.state_model.config.audio_traj,
                    content="SPECT",
                ),
                self.state_model.dimensions,
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
            self.state_model.tail_s,
            self.state_model.data[name].duration_s,
        )

        self.root.temporal_view.update_plot(cursor=True, variable=True)
        if self.state_model.audio_spect is not None:
            self.root.freq_domain_view.update_plot()
        self.root.spatial_view.update_plot(points=True)

    def _todo(self, action: str):
        return lambda: print(f"TODO: {action}")
