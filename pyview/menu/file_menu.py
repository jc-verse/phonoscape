from typing import TYPE_CHECKING

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu

if TYPE_CHECKING:
    from .menu_bar import MenuBar

from ..data.process import get_plotting_data
from ..state import ScalarTrajDisplay


class FileMenu(QMenu):
    def __init__(self, parent: MenuBar):
        super().__init__("File", parent)

        self.state_model = parent.state_model
        self.root = parent.root

        variables_menu = QMenu("Variables", self)
        self.variable_action_group = QActionGroup(self)
        self.variable_action_group.setExclusive(True)

        current_variable = parent.root.selected_variable_var.get()

        for name in self.state_model.variable_names:
            action = QAction(name, self)
            action.setCheckable(True)
            action.setChecked(name == current_variable)
            action.triggered.connect(
                lambda checked=False, name=name: self._on_variable_change(name)
            )

            self.variable_action_group.addAction(action)
            variables_menu.addAction(action)

        self.addMenu(variables_menu)
        self.addSeparator()

        save_menu = QMenu("Save", self)
        save_menu.addAction(
            "Save all but selection...",
            parent._todo("Save all but selection"),
        )
        save_menu.addAction(
            "Save selection only...",
            parent._todo("Save selection only"),
        )

        self.addMenu(save_menu)
        self.addAction("Export...", parent._todo("Export"))
        self.addAction("Close window", parent._todo("Close window"))
        self.addAction("Close all", parent._todo("Close all"))

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
