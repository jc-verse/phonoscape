import tkinter as tk
from tkinter import ttk
from collections.abc import Callable


class VariableDropdown(ttk.Combobox):
    def __init__(
        self,
        parent: tk.Widget,
        *,
        variable_names: list[str],
        on_variable_changed: Callable[[str], None],
    ):
        self._selected_variable = tk.StringVar(value=variable_names[0])
        super().__init__(
            parent,
            textvariable=self._selected_variable,
            values=variable_names,
            state="readonly",
        )
        self.bind("<<ComboboxSelected>>", self._on_selection_changed)
        self._on_variable_changed = on_variable_changed

    def _on_selection_changed(self, _event: tk.Event | None = None) -> None:
        self._on_variable_changed(self._selected_variable.get())
