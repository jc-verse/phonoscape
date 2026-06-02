from typing import TYPE_CHECKING
import tkinter as tk
from tkinter import ttk, messagebox

if TYPE_CHECKING:
    from ..menu.view_menu import ViewMenu


views = {
    "2D view (1)": (90, 0, 90),
    "2D view (2)": (0, -90, 0),
    "2D view (3)": (0, -180, 0),
    "3D view (1)": (18, 20, 0),
    "3D view (2)": (-30, -62.5, 0),
    "3D view (3)": (-20, -117, 0),
}


def open_spatial_view_dialog(parent: ViewMenu) -> None:
    dialog = tk.Toplevel(parent)
    dialog.withdraw()
    dialog.title("Specify view")
    dialog.transient(parent)
    dialog.resizable(False, False)

    main = ttk.Frame(dialog, padding=12)
    main.grid(row=0, column=0, sticky="nsew")

    azim_var = tk.StringVar(value=str(parent.root.spatial_view.ax.azim))
    elev_var = tk.StringVar(value=str(parent.root.spatial_view.ax.elev))
    roll_var = tk.StringVar(value=str(parent.root.spatial_view.ax.roll))

    ttk.Label(main, text="azim").grid(row=0, column=0, sticky="e", padx=(0, 8), pady=4)
    ttk.Entry(main, textvariable=azim_var, width=12).grid(row=0, column=1, sticky="ew", pady=4)

    ttk.Label(main, text="elev").grid(row=1, column=0, sticky="e", padx=(0, 8), pady=4)
    ttk.Entry(main, textvariable=elev_var, width=12).grid(row=1, column=1, sticky="ew", pady=4)

    ttk.Label(main, text="roll").grid(row=2, column=0, sticky="e", padx=(0, 8), pady=4)
    ttk.Entry(main, textvariable=roll_var, width=12).grid(row=2, column=1, sticky="ew", pady=4)

    buttons = ttk.Frame(main)
    buttons.grid(row=3, column=0, columnspan=2, sticky="e", pady=(12, 0))

    def on_ok() -> None:
        try:
            azim = float(azim_var.get())
            elev = float(elev_var.get())
            roll = float(roll_var.get())
        except ValueError:
            messagebox.showerror(
                "Invalid view",
                "azim, elev, and roll must be numbers.",
                parent=dialog,
            )
            return

        dialog.destroy()
        matching_view = None
        for label, (velev, vazim, vroll) in views.items():
            if azim == vazim and elev == velev and roll == vroll:
                matching_view = label
                break
        if matching_view is not None:
            parent.view_option.set(matching_view)
            parent._view_init()
        else:
            parent.view_option.set("")  # Clear selection in menu.

            parent.root.spatial_view.ax.view_init(elev=elev, azim=azim, roll=roll)
            parent.root.spatial_view.canvas.draw_idle()

    def on_cancel() -> None:
        dialog.destroy()

    ttk.Button(buttons, text="OK", command=on_ok).grid(row=0, column=0, padx=(0, 6))
    ttk.Button(buttons, text="Cancel", command=on_cancel).grid(row=0, column=1)

    dialog.bind("<Return>", lambda _event: on_ok())
    dialog.bind("<Escape>", lambda _event: on_cancel())
    dialog.protocol("WM_DELETE_WINDOW", on_cancel)

    dialog.update_idletasks()
    x = (
        parent.root.winfo_x()
        + (parent.root.winfo_width() - dialog.winfo_reqwidth()) // 2
    )
    y = (
        parent.root.winfo_y()
        + (parent.root.winfo_height() - dialog.winfo_reqheight()) // 2
    )
    dialog.geometry(f"+{x}+{y}")
    dialog.deiconify()
    dialog.grab_set()
    dialog.lift()
    dialog.focus_set()
    parent.wait_window(dialog)
