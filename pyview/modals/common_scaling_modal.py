from typing import TYPE_CHECKING
import tkinter as tk
from tkinter import ttk, messagebox

if TYPE_CHECKING:
    from ..menu.view_menu import ViewMenu


def open_common_scaling_dialog(parent: ViewMenu) -> None:
    dialog = tk.Toplevel(parent)
    dialog.withdraw()
    dialog.title("Set Common Scaling")
    dialog.transient(parent)
    dialog.resizable(False, False)

    main = ttk.Frame(dialog, padding=12)
    main.grid(row=0, column=0, sticky="nsew")

    # TODO: Real state
    scaling = [0.0, 0.0, 0.0]

    mvt_var = tk.StringVar(value=f"{scaling[0]:.2f}")
    vel_var = tk.StringVar(value=f"{scaling[1]:.2f}")
    acc_var = tk.StringVar(value=f"{scaling[2]:.2f}")

    ttk.Label(main, text="Mvt").grid(row=0, column=0, sticky="e", padx=(0, 6))
    ttk.Entry(main, textvariable=mvt_var, width=10).grid(
        row=0, column=1, sticky="w", padx=(0, 12)
    )

    ttk.Label(main, text="Vel").grid(row=0, column=2, sticky="e", padx=(0, 6))
    ttk.Entry(main, textvariable=vel_var, width=10).grid(
        row=0, column=3, sticky="w", padx=(0, 12)
    )

    ttk.Label(main, text="Acc").grid(row=0, column=4, sticky="e", padx=(0, 6))
    ttk.Entry(main, textvariable=acc_var, width=10).grid(row=0, column=5, sticky="w")

    buttons = ttk.Frame(main)
    buttons.grid(row=1, column=0, columnspan=6, pady=(16, 0))

    def on_ok() -> None:
        # TODO: Update state
        dialog.destroy()

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
