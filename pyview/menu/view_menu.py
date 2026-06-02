from typing import TYPE_CHECKING
import tkinter as tk

if TYPE_CHECKING:
    from .menu_bar import MenuBar
from ..state import PyViewState
from ..modals.common_scaling_modal import open_common_scaling_dialog
from ..modals.temporal_config_modal import open_tempcfg_dialog
from ..modals.spatial_view_modal import open_spatial_view_dialog, views


class ViewMenu(tk.Menu):
    def __init__(self, parent: MenuBar, state_model: PyViewState):
        super().__init__(parent, tearoff=False)
        self.state_model = state_model
        self.parent = parent
        self.root = parent.parent
        self.add_command(
            label="Temporal layout...", command=lambda: open_tempcfg_dialog(self)
        )
        spatial_menu = tk.Menu(self, tearoff=False)
        self.hide_spline_var = tk.BooleanVar(value=False)
        spatial_menu.add_checkbutton(
            label="Hide spline",
            variable=self.hide_spline_var,
            command=self._hide_spline,
        )
        spatial_menu.add_separator()
        self.free_rotate_var = tk.BooleanVar(value=False)
        spatial_menu.add_checkbutton(
            label="Free rotate",
            variable=self.free_rotate_var,
            command=self._free_rotate,
        )
        self._free_rotate()
        self.root.spatial_view.canvas.mpl_connect(
            "button_release_event", self._on_spatial_axis_rotate
        )
        spatial_menu.add_separator()

        self.view_option = tk.StringVar(value="2D view (2)")
        for label in views.keys():
            spatial_menu.add_radiobutton(
                label=label,
                variable=self.view_option,
                value=label,
                command=self._view_init,
            )
        self._view_init()
        spatial_menu.add_command(
            label="Specify view...", command=lambda: open_spatial_view_dialog(self)
        )
        self.add_cascade(label="Spatial options", menu=spatial_menu)
        self.add_command(
            label="Set common scaling...",
            command=lambda: open_common_scaling_dialog(self),
        )

    def _hide_spline(self):
        if self.root.spatial_view.spline_artist is not None:
            self.root.spatial_view.spline_artist.set_visible(
                not self.hide_spline_var.get()
            )

    def _free_rotate(self):
        free_rotate = self.free_rotate_var.get()
        if free_rotate:
            self.root.spatial_view.ax.mouse_init()
        else:
            self.root.spatial_view.ax.disable_mouse_rotation()

    def _view_init(self):
        elev, azim, roll = views[self.view_option.get()]
        self.root.spatial_view.ax.view_init(elev=elev, azim=azim, roll=roll)
        self.root.spatial_view.canvas.draw_idle()

    def _on_spatial_axis_rotate(self, event):
        if not self.free_rotate_var.get():
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
            self.view_option.set(matching_view)
            self._view_init()
        else:
            self.view_option.set("")  # Clear selection in menu.
