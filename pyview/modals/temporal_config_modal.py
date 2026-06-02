from typing import Literal, TYPE_CHECKING

import tkinter as tk
from tkinter import ttk

if TYPE_CHECKING:
    from ..menu.view_menu import ViewMenu
from ..state import ScalarTrajDisplay, SpatialTrajDisplay


def open_tempcfg_dialog(parent: ViewMenu) -> None:
    dialog = tk.Toplevel(parent)
    dialog.withdraw()
    dialog.title("Configure temporal layout")
    dialog.transient(parent)
    dialog.rowconfigure(0, weight=1)
    dialog.columnconfigure(0, weight=1)

    loaded_names = list(parent.state_model.selected_value.trajectories.keys())
    displayed_specs = list(parent.state_model.config.temporal_disp_specs)

    main = ttk.Frame(dialog, padding=12)
    main.grid(row=0, column=0, sticky="nsew")
    main.columnconfigure(0, weight=1)
    main.columnconfigure(1, weight=0)
    main.columnconfigure(2, weight=1)

    main.rowconfigure(0, weight=0)
    main.rowconfigure(1, weight=1)
    main.rowconfigure(5, weight=0)
    main.rowconfigure(6, weight=0)
    main.rowconfigure(7, weight=0)

    ttk.Label(main, text="Loaded").grid(row=0, column=0, sticky="w")
    ttk.Label(main, text="Displayed").grid(row=0, column=2, sticky="w")

    loaded_var = tk.Variable(value=loaded_names)
    displayed_var = tk.Variable(value=[str(spec) for spec in displayed_specs])

    loaded_list = tk.Listbox(
        main,
        listvariable=loaded_var,
        selectmode="extended",
        exportselection=False,
        height=9,
        width=22,
    )
    displayed_list = tk.Listbox(
        main,
        listvariable=displayed_var,
        selectmode="extended",
        exportselection=False,
        height=9,
        width=22,
    )

    loaded_list.grid(row=1, column=0, sticky="nsew", pady=(4, 10))
    displayed_list.grid(row=1, column=2, sticky="nsew", pady=(4, 10))

    middle = ttk.Frame(main)
    middle.grid(row=1, column=1, padx=10, pady=(18, 10), sticky="n")

    xfer_button = ttk.Button(middle, text=">", width=1)
    delete_button = ttk.Button(middle, text="x", width=1)
    up_button = ttk.Button(middle, text="^", width=1)
    down_button = ttk.Button(middle, text="v", width=1)

    xfer_button.grid(row=0, column=0, pady=3)
    delete_button.grid(row=1, column=0, pady=3)
    up_button.grid(row=2, column=0, pady=3)
    down_button.grid(row=3, column=0, pady=3)

    detail = ttk.Frame(main)
    detail.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(4, 0))
    detail.columnconfigure(1, weight=1)

    ttk.Label(detail, text="Content:").grid(row=0, column=0, sticky="e", padx=(0, 8))

    content_var = tk.StringVar()
    content_combo = ttk.Combobox(
        detail,
        textvariable=content_var,
        state="disabled",
        values=[],
        width=22,
    )
    content_combo.grid(row=0, column=1, sticky="w")

    comps = ttk.Frame(main)
    comps.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(10, 0))

    ttk.Label(comps, text="Components:").grid(row=0, column=0, sticky="e", padx=(0, 8))

    x_var = tk.BooleanVar(value=False)
    y_var = tk.BooleanVar(value=False)
    z_var = tk.BooleanVar(value=False)

    x_check = ttk.Checkbutton(comps, text="X", variable=x_var)
    y_check = ttk.Checkbutton(comps, text="Y", variable=y_var)
    z_check = ttk.Checkbutton(comps, text="Z", variable=z_var)

    x_check.grid(row=0, column=1, sticky="w")
    y_check.grid(row=0, column=2, sticky="w")
    z_check.grid(row=0, column=3, sticky="w")

    buttons = ttk.Frame(main)
    buttons.grid(row=7, column=0, columnspan=3, pady=(16, 0))

    ok_button = ttk.Button(buttons, text="OK")
    cancel_button = ttk.Button(buttons, text="Cancel")

    ok_button.grid(row=0, column=0, padx=6)
    cancel_button.grid(row=0, column=1, padx=6)

    def selected_displayed_index() -> int | None:
        indices = displayed_list.curselection()
        if len(indices) != 1:
            return None
        return indices[0]

    def set_component_state(state: Literal["normal", "disabled"]) -> None:
        x_check.configure(state=state)
        y_check.configure(state=state)
        z_check.configure(state=state)

    def refresh_displayed_listbox() -> None:
        displayed_var.set([str(spec) for spec in displayed_specs])

    def refresh_button_states() -> None:
        loaded_sel = loaded_list.curselection()
        displayed_sel = displayed_list.curselection()

        xfer_button.configure(state="normal" if loaded_sel else "disabled")
        delete_button.configure(state="normal" if displayed_sel else "disabled")

        if len(displayed_sel) == 1:
            idx = displayed_sel[0]
            up_button.configure(state="normal" if idx > 0 else "disabled")
            down_button.configure(
                state="normal" if idx < len(displayed_specs) - 1 else "disabled"
            )
        else:
            up_button.configure(state="disabled")
            down_button.configure(state="disabled")

    def refresh_detail_controls() -> None:
        idx = selected_displayed_index()
        if idx is None:
            content_combo.configure(state="disabled", values=[])
            content_var.set("")
            x_var.set(False)
            y_var.set(False)
            z_var.set(False)
            set_component_state("disabled")
            return

        spec = displayed_specs[idx]

        if isinstance(spec, ScalarTrajDisplay):
            content_combo.configure(
                state="readonly",
                values=["SIGNAL", "SPECT", "RMS", "ZC", "VEL", "ABSVEL"],
            )
            content_var.set(spec.content)
            x_var.set(False)
            y_var.set(False)
            z_var.set(False)
            set_component_state("disabled")

        elif isinstance(spec, SpatialTrajDisplay):
            content_combo.configure(
                state="readonly",
                values=["movement", "velocity", "acceleration"],
            )
            content_var.set(spec.content)
            x_var.set("x" in spec.components)
            y_var.set("y" in spec.components)
            z_var.set("z" in spec.components)
            set_component_state("normal")

        else:
            raise Exception(f"Unknown spec type: {spec}")

    def rewrite_selected_spec() -> None:
        idx = selected_displayed_index()
        if idx is None:
            return

        old = displayed_specs[idx]

        if isinstance(old, ScalarTrajDisplay):
            displayed_specs[idx] = ScalarTrajDisplay(
                traj_name=old.traj_name,
                content=content_var.get(),
            )

        elif isinstance(old, SpatialTrajDisplay):
            components = []
            if x_var.get():
                components.append("x")
            if y_var.get():
                components.append("y")
            if z_var.get():
                components.append("z")

            # Avoid invalid empty component list.
            if not components:
                components = list(old.components)

            displayed_specs[idx] = SpatialTrajDisplay(
                traj_name=old.traj_name,
                content=content_var.get(),
                components=components,
            )

        refresh_displayed_listbox()
        displayed_list.selection_set(idx)
        displayed_list.activate(idx)
        refresh_detail_controls()
        refresh_button_states()

    def on_loaded_select(_event=None) -> None:
        displayed_list.selection_clear(0, tk.END)
        refresh_detail_controls()
        refresh_button_states()

    def on_displayed_select(_event=None) -> None:
        loaded_list.selection_clear(0, tk.END)
        refresh_detail_controls()
        refresh_button_states()

    def on_xfer() -> None:
        for idx in loaded_list.curselection():
            traj_name = loaded_list.get(idx)
            traj = parent.state_model.selected_value.trajectories[traj_name]
            if traj.kind == "spatial":
                displayed_specs.append(
                    SpatialTrajDisplay(
                        traj_name=traj_name,
                        content="movement",
                        components=["x", "y", "z"][: traj.dimensions],
                    )
                )
            else:
                displayed_specs.append(
                    ScalarTrajDisplay(traj_name=traj_name, content="SIGNAL")
                )

        refresh_displayed_listbox()
        # No need to refresh_detail_controls because the selection is the same
        refresh_button_states()

    def on_delete() -> None:
        indices = displayed_list.curselection()
        if not indices:
            return

        for idx in reversed(indices):
            del displayed_specs[idx]

        refresh_displayed_listbox()
        refresh_detail_controls()
        refresh_button_states()

    def on_move(delta: Literal[1, -1]) -> None:
        idx = selected_displayed_index()
        if idx is None:
            return

        new_idx = idx + delta
        if new_idx < 0 or new_idx >= len(displayed_specs):
            return

        displayed_specs[idx], displayed_specs[new_idx] = (
            displayed_specs[new_idx],
            displayed_specs[idx],
        )

        refresh_displayed_listbox()
        displayed_list.selection_clear(0, tk.END)
        displayed_list.selection_set(new_idx)
        displayed_list.activate(new_idx)
        refresh_detail_controls()
        refresh_button_states()

    def on_ok() -> None:
        parent.state_model.config.temporal_disp_specs = displayed_specs
        parent.root.temporal_view.reset_plot()
        dialog.destroy()

    def on_cancel() -> None:
        dialog.destroy()

    loaded_list.bind("<<ListboxSelect>>", on_loaded_select)
    displayed_list.bind("<<ListboxSelect>>", on_displayed_select)

    xfer_button.configure(command=on_xfer)
    delete_button.configure(command=on_delete)
    up_button.configure(command=lambda: on_move(-1))
    down_button.configure(command=lambda: on_move(1))

    content_combo.bind("<<ComboboxSelected>>", lambda _event: rewrite_selected_spec())
    x_check.configure(command=rewrite_selected_spec)
    y_check.configure(command=rewrite_selected_spec)
    z_check.configure(command=rewrite_selected_spec)

    ok_button.configure(command=on_ok)
    cancel_button.configure(command=on_cancel)

    dialog.bind("<Return>", lambda _event: on_ok())
    dialog.bind("<Escape>", lambda _event: on_cancel())
    dialog.protocol("WM_DELETE_WINDOW", on_cancel)

    refresh_detail_controls()

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
    dialog.lift()
    dialog.focus_set()
    dialog.grab_set()
    parent.wait_window(dialog)
