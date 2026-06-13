from typing import TYPE_CHECKING

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu

if TYPE_CHECKING:
    from .menu_bar import MenuBar

from ..modals.common_scaling_modal import open_common_scaling_dialog
from ..modals.temporal_config_modal import open_tempcfg_dialog
from ..modals.spatial_view_modal import open_spatial_view_dialog, views


class ViewMenu(QMenu):
    def __init__(self, parent: MenuBar):
        super().__init__("View", parent)

        self.state = parent.state
        self.root = parent.root

        self.addAction("Temporal layout...", lambda: open_tempcfg_dialog(self), shortcut="Ctrl+C")
        self.addAction(
            "Set common scaling...",
            lambda: open_common_scaling_dialog(self),
        )
        self.addSeparator()

        self.hide_spline_action = QAction(
            "Hide spline",
            self,
            checkable=True,
            checked=False,
            enabled=bool(self.state.app_config.spline_trajs),
        )
        self.hide_spline_action.triggered.connect(self._hide_spline)
        self.addAction(self.hide_spline_action)

        spatial_history_menu = QMenu("Spatial history", self)
        spatial_history_group = QActionGroup(self)
        spatial_history_group.setExclusive(True)
        for label, value in [("None", False), ("History", True), ("Hue", "hue")]:
            action = QAction(label, self, checkable=True, checked=label == "None")
            action.triggered.connect(
                lambda checked=False, value=value: self.root.spatial_view.update_plot(
                    history_mode=value
                )
            )
            spatial_history_group.addAction(action)
            spatial_history_menu.addAction(action)
        self.addMenu(spatial_history_menu)

        if self.state.app_config.dimensions == 3:
            spatial_3d_view_menu = QMenu("Spatial 3D view", self)
            self.view_action_group = QActionGroup(self)
            self.view_action_group.setExclusive(True)
            self.view_actions: dict[str, QAction] = {}

            for label in views.keys():
                action = QAction(label, self, checkable=True, checked=False)
                action.triggered.connect(
                    lambda checked=False, label=label: self._set_view_option(label)
                )
                self.view_action_group.addAction(action)
                spatial_3d_view_menu.addAction(action)
                self.view_actions[label] = action

            spatial_3d_view_menu.addSeparator()

            spatial_3d_view_menu.addAction(
                "Specify view...",
                lambda: open_spatial_view_dialog(self),
            )
            spatial_3d_view_menu.addSeparator()

            self.free_rotate_action = QAction(
                "Free rotate", self, checkable=True, checked=False
            )
            self.free_rotate_action.triggered.connect(self._free_rotate)
            spatial_3d_view_menu.addAction(self.free_rotate_action)

            self.root.spatial_view.canvas.mpl_connect(
                "motion_notify_event", self._on_spatial_axis_rotate
            )
            self.root.spatial_view.canvas.mpl_connect(
                "button_release_event", self._on_spatial_axis_rotate_complete
            )

            self.addMenu(spatial_3d_view_menu)

            self._set_view(self.state.view)
            self.root.readout.clear_readout()
            self._free_rotate()

        self.addSeparator()
        # On macOS, this menu includes an "Enter full screen" action. It's useful
        # but its icon shouldn't affect alignment of other items, so add a separator.

    def _hide_spline(self) -> None:
        if self.root.spatial_view.spline_artist is not None:
            self.root.spatial_view.spline_artist.set_visible(
                not self.hide_spline_action.isChecked()
            )
            self.root.spatial_view.canvas.draw_idle()

    def _free_rotate(self) -> None:
        free_rotate = self.free_rotate_action.isChecked()
        if free_rotate:
            self.root.spatial_view.ax.mouse_init()
        else:
            self.root.spatial_view.ax.disable_mouse_rotation()

    def _set_view_option(self, label: str) -> None:
        elev, azim, roll = views[label]
        self.root.state.view = (elev, azim, roll)
        self.root.readout.readout_camera(elev=elev, azim=azim, roll=roll)
        self.root.spatial_view.ax.view_init(elev=elev, azim=azim, roll=roll)
        self.root.spatial_view.canvas.draw_idle()

    def _set_view(self, view: tuple[float, float, float]) -> None:
        matching_view = None
        for label, (velev, vazim, vroll) in views.items():
            if view[0] == velev and view[1] == vazim and view[2] == vroll:
                matching_view = label
                break
        if matching_view is not None:
            action = self.view_actions[matching_view]
            action.blockSignals(True)
            action.setChecked(True)
            action.blockSignals(False)
        elev, azim, roll = view
        self.root.state.view = view
        self.root.readout.readout_camera(elev=elev, azim=azim, roll=roll)
        self.root.spatial_view.ax.view_init(elev=elev, azim=azim, roll=roll)
        self.root.spatial_view.canvas.draw_idle()

    def _clear_view_selection(self) -> None:
        self.view_action_group.setExclusive(False)
        for action in self.view_actions.values():
            action.setChecked(False)
        self.view_action_group.setExclusive(True)

    def _on_spatial_axis_rotate(self, event) -> None:
        if not self.free_rotate_action.isChecked():
            return
        if event.inaxes is not self.root.spatial_view.ax:
            return
        self.root.readout.readout_camera(
            elev=self.root.spatial_view.ax.elev,
            azim=self.root.spatial_view.ax.azim,
            roll=self.root.spatial_view.ax.roll,
        )

    def _on_spatial_axis_rotate_complete(self, event) -> None:
        if not self.free_rotate_action.isChecked():
            return
        if event.inaxes is not self.root.spatial_view.ax:
            return

        view = (
            self.root.spatial_view.ax.elev,
            self.root.spatial_view.ax.azim,
            self.root.spatial_view.ax.roll,
        )
        self.root.state.view = view

        matching_view = None
        for label, (velev, vazim, vroll) in views.items():
            if (
                abs(view[0] - velev) < 5
                and abs(view[1] - vazim) < 5
                and abs(view[2] - vroll) < 5
            ):
                matching_view = label
                break
        if matching_view is not None:
            self._set_view_option(matching_view)
        else:
            self._clear_view_selection()
