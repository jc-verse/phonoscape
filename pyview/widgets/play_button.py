import tkinter as tk
from tkinter import ttk
from collections.abc import Callable


class SplitPlayButton(ttk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        *,
        on_play: Callable[[str], None],
        modes: tuple[str, ...] = (
            "Entire file",
            "To cursor",
            "From cursor",
            "150ms @ cursor",
        ),
    ):
        super().__init__(parent, style="SplitButton.TFrame", padding=0)

        self._on_play = on_play
        self.play_mode = tk.StringVar(value=modes[0])

        self.menu = tk.Menu(self, tearoff=False)
        for mode in modes:
            self.menu.add_radiobutton(
                label=mode,
                variable=self.play_mode,
                value=mode,
            )

        self.play_part = ttk.Button(
            self,
            text="Play",
            style="SplitButtonPart.TButton",
            command=self._play,
        )
        self.play_part.grid(row=0, column=0, sticky="nsew")

        self.chevron_part = ttk.Button(
            self,
            text="▾",
            width=2,
            style="SplitButtonPart.TButton",
        )
        self.chevron_part.grid(row=0, column=1, sticky="nsew")
        self.chevron_part.bind("<Button-1>", self._show_menu)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)

    def _show_menu(self, event: tk.Event) -> None:
        self.menu.tk_popup(event.x_root, event.y_root)

    def _play(self) -> None:
        self._on_play(self.play_mode.get())
