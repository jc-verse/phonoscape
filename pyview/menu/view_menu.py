from typing import TYPE_CHECKING
import tkinter as tk
from tkinter import ttk, messagebox

if TYPE_CHECKING:
    from .menu_bar import MenuBar
from ..state import PyViewState

views = {
    "2D view (1)": (90, 0, 90),
    "2D view (2)": (0, -90, 0),
    "2D view (3)": (0, -180, 0),
    "3D view (1)": (18, 20, 0),
    "3D view (2)": (-30, -62.5, 0),
    "3D view (3)": (-20, -117, 0),
}


class ViewMenu(tk.Menu):
    def __init__(self, parent: MenuBar, state_model: PyViewState):
        super().__init__(parent, tearoff=False)
        self.state_model = state_model
        self.parent = parent
        self.root = parent.parent
        self.add_command(
            label="Temporal layout...", command=self.parent._todo("Temporal layout")
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
        spatial_menu.add_command(label="Specify view...", command=self._specify_view)
        self.add_cascade(label="Spatial options", menu=spatial_menu)
        self.add_command(
            label="Set common scaling...",
            command=self.parent._todo("Set common scaling"),
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

    def _specify_view(self) -> None:
        self.view_option.set("")  # Clear selection in menu.
        dialog = tk.Toplevel(self)
        dialog.withdraw()
        dialog.title("Specify view")
        dialog.transient(self)
        dialog.resizable(False, False)

        # Make it modal.
        dialog.grab_set()

        main = ttk.Frame(dialog, padding=12)
        main.grid(row=0, column=0, sticky="nsew")

        azim_var = tk.StringVar(value=str(self.root.spatial_view.ax.azim))
        elev_var = tk.StringVar(value=str(self.root.spatial_view.ax.elev))

        ttk.Label(main, text="azim").grid(
            row=0, column=0, sticky="e", padx=(0, 8), pady=4
        )
        azim_entry = ttk.Entry(main, textvariable=azim_var, width=12)
        azim_entry.grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(main, text="elev").grid(
            row=1, column=0, sticky="e", padx=(0, 8), pady=4
        )
        elev_entry = ttk.Entry(main, textvariable=elev_var, width=12)
        elev_entry.grid(row=1, column=1, sticky="ew", pady=4)

        buttons = ttk.Frame(main)
        buttons.grid(row=2, column=0, columnspan=2, sticky="e", pady=(12, 0))

        def on_ok() -> None:
            try:
                azim = float(azim_var.get())
                elev = float(elev_var.get())
            except ValueError:
                messagebox.showerror(
                    "Invalid view",
                    "azim and elev must be numbers.",
                    parent=dialog,
                )
                return

            dialog.destroy()

            self.root.spatial_view.ax.view_init(elev=elev, azim=azim)
            self.root.spatial_view.canvas.draw_idle()

        def on_cancel() -> None:
            dialog.destroy()

        ttk.Button(buttons, text="OK", command=on_ok).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(buttons, text="Cancel", command=on_cancel).grid(row=0, column=1)

        dialog.bind("<Return>", lambda _event: on_ok())
        dialog.bind("<Escape>", lambda _event: on_cancel())

        azim_entry.focus_set()
        azim_entry.selection_range(0, tk.END)

        # Center relative to parent after geometry is computed.
        dialog.update_idletasks()
        x = (
            self.root.winfo_rootx()
            + (self.root.winfo_width() - dialog.winfo_reqwidth()) // 2
        )
        y = (
            self.root.winfo_rooty()
            + (self.root.winfo_height() - dialog.winfo_reqheight()) // 2
        )
        dialog.geometry(f"+{x}+{y}")
        dialog.deiconify()

        self.wait_window(dialog)
