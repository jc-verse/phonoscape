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

        self.state_model = parent.state_model
        self.root = parent.root

        self.addAction("Temporal layout...", lambda: open_tempcfg_dialog(self))
        self.addAction(
            "Set common scaling...",
            lambda: open_common_scaling_dialog(self),
        )
        self.addSeparator()

        spatial_menu = QMenu("Spatial options", self)

        self.hide_spline_action = QAction("Hide spline", self)
        self.hide_spline_action.setCheckable(True)
        self.hide_spline_action.setChecked(False)
        self.hide_spline_action.triggered.connect(self._hide_spline)
        spatial_menu.addAction(self.hide_spline_action)
        if not self.state_model.app_config.spline_trajs:
            self.hide_spline_action.setEnabled(False)

        if self.state_model.dimensions == 3:
            spatial_menu.addSeparator()

            self.free_rotate_action = QAction("Free rotate", self)
            self.free_rotate_action.setCheckable(True)
            self.free_rotate_action.setChecked(False)
            self.free_rotate_action.triggered.connect(self._free_rotate)
            spatial_menu.addAction(self.free_rotate_action)

            self._free_rotate()

            self.root.spatial_view.canvas.mpl_connect(
                "button_release_event", self._on_spatial_axis_rotate
            )

            spatial_menu.addSeparator()

            self.view_action_group = QActionGroup(self)
            self.view_action_group.setExclusive(True)
            self.view_actions: dict[str, QAction] = {}

            self.view_option = "2D view (2)"

            for label in views.keys():
                action = QAction(label, self)
                action.setCheckable(True)
                action.setChecked(label == self.view_option)
                action.triggered.connect(
                    lambda checked=False, label=label: self._set_view_option(label)
                )
                self.view_action_group.addAction(action)
                spatial_menu.addAction(action)
                self.view_actions[label] = action

            self._view_init()

            spatial_menu.addAction(
                "Specify view...",
                lambda: open_spatial_view_dialog(self),
            )

        self.addMenu(spatial_menu)

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
        self.view_option = label
        self._view_init()

    def _view_init(self) -> None:
        elev, azim, roll = views[self.view_option]
        self.root.spatial_view.ax.view_init(elev=elev, azim=azim, roll=roll)
        self.root.spatial_view.canvas.draw_idle()

    def _clear_view_selection(self) -> None:
        self.view_action_group.setExclusive(False)
        for action in self.view_actions.values():
            action.setChecked(False)
        self.view_action_group.setExclusive(True)
        self.view_option = ""

    def _on_spatial_axis_rotate(self, event) -> None:
        if not self.free_rotate_action.isChecked():
            return
        if event.inaxes is not self.root.spatial_view.ax:
            return

        view = (
            self.root.spatial_view.ax.elev,
            self.root.spatial_view.ax.azim,
            self.root.spatial_view.ax.roll,
        )

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
            self.view_option = matching_view
            action = self.view_actions[matching_view]
            action.blockSignals(True)
            action.setChecked(True)
            action.blockSignals(False)
            self._view_init()
        else:
            self._clear_view_selection()
