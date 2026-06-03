from typing import TYPE_CHECKING, Literal
import tkinter as tk
from tkinter import ttk, messagebox

if TYPE_CHECKING:
    from ..views.temporal_view import TemporalView


def open_label_dialog(
    parent: TemporalView,
    cursor_s: float,
    action: Literal["create"] | tuple[Literal["edit"], int],
) -> None:
    dialog = tk.Toplevel(parent)
    dialog.withdraw()
    dialog.title(
        f"{action[0].capitalize() if isinstance(action, tuple) else action.capitalize()} label"
    )
    dialog.transient(parent.winfo_toplevel())
    dialog.resizable(False, False)

    main = ttk.Frame(dialog, padding=12)
    main.grid(row=0, column=0, sticky="nsew")

    name_var = tk.StringVar(value="")
    offset_ms_var = tk.StringVar(value=f"{cursor_s * 1000.0:.1f}")
    note_var = tk.StringVar(value="")

    ttk.Label(main, text="Name:", anchor="e").grid(
        row=0, column=0, sticky="e", padx=(0, 5), pady=(0, 8)
    )
    ttk.Entry(main, textvariable=name_var, width=14).grid(
        row=0, column=1, sticky="ew", pady=(0, 8)
    )

    ttk.Label(main, text="Offset (ms):", anchor="e").grid(
        row=0, column=2, sticky="e", padx=(12, 5), pady=(0, 8)
    )
    ttk.Entry(main, textvariable=offset_ms_var, width=10).grid(
        row=0, column=3, sticky="ew", pady=(0, 8)
    )

    ttk.Label(main, text="Note:", anchor="e").grid(
        row=1, column=0, sticky="e", padx=(0, 5), pady=(0, 16)
    )
    ttk.Entry(main, textvariable=note_var, width=30).grid(
        row=1, column=1, columnspan=3, sticky="ew", pady=(0, 16)
    )

    buttons = ttk.Frame(main)
    buttons.grid(row=2, column=0, columnspan=4)

    def on_ok() -> None:
        try:
            offset_ms = float(offset_ms_var.get())
        except ValueError:
            messagebox.showerror(
                "Invalid offset", "Offset must be a number.", parent=dialog
            )
            return
        name = name_var.get().strip()
        if not name:
            messagebox.showerror("Invalid name", "Name cannot be empty.", parent=dialog)
            return
        note = note_var.get().strip()
        if action == "create":
            new_label = parent.state_model.add_label(name, offset_ms / 1000.0, note)
            parent.update_plot(labels=[new_label])
        else:
            new_label, old_label = parent.state_model.edit_label(
                action[1], name, offset_ms / 1000.0, note
            )
            parent.update_plot(labels=[new_label, old_label])
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
        parent.parent.winfo_x()
        + (parent.parent.winfo_width() - dialog.winfo_reqwidth()) // 2
    )
    y = (
        parent.parent.winfo_y()
        + (parent.parent.winfo_height() - dialog.winfo_reqheight()) // 2
    )
    dialog.geometry(f"+{x}+{y}")
    dialog.deiconify()
    dialog.grab_set()
    dialog.lift()
    dialog.focus_set()
    parent.wait_window(dialog)
