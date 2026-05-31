import tkinter as tk
from tkinter import ttk
import sounddevice as sd

from ..state import PyViewState

modes = (
    "Selection",
    "Entire file",
    "To cursor",
    "From cursor",
    "150ms @ cursor",
)


def play(state_model: PyViewState) -> None:
    audio_traj = state_model.config.audio_traj
    if audio_traj is None:
        print("No audio trajectory configured.")
        return
    traj = state_model.selected_value.trajectories[audio_traj]
    play_data = None
    head_index = int(state_model.head_s * traj.sample_rate_hz)
    cursor_index = int(state_model.cursor_s * traj.sample_rate_hz)
    tail_index = int(state_model.tail_s * traj.sample_rate_hz)
    mode = state_model.play_mode.get()
    if mode == "Selection":
        play_data = traj.data[head_index:tail_index]
    elif mode == "Entire file":
        play_data = traj.data
    elif mode == "To cursor":
        play_data = (
            traj.data[head_index:cursor_index]
            if cursor_index > head_index
            else traj.data[head_index:tail_index]
        )
    elif mode == "From cursor":
        play_data = (
            traj.data[cursor_index:tail_index]
            if cursor_index < tail_index
            else traj.data[head_index:tail_index]
        )
    elif mode == "150ms @ cursor":
        half_window = int(0.15 * traj.sample_rate_hz / 2)
        start = max(head_index, cursor_index - half_window)
        end = min(tail_index, cursor_index + half_window)
        play_data = traj.data[start:end]
    else:
        print(f"Unknown play mode: {mode}")
        return
    if play_data is not None and len(play_data) > 0:
        sd.play(play_data, samplerate=traj.sample_rate_hz)


class PlayButton(ttk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        state_model: PyViewState,
    ):
        super().__init__(parent)

        self.state_model = state_model

        self.menu = tk.Menu(self, tearoff=False)
        for mode in modes:
            self.menu.add_radiobutton(
                label=mode, variable=self.state_model.play_mode, value=mode
            )

        btn = ttk.Button(self, text="Play", command=lambda: play(self.state_model))
        btn.grid(row=0, column=0, sticky="nsew")
        btn.bind("<Button-3>", self._show_menu)
        btn.bind("<Button-2>", self._show_menu)
        btn.bind("<Control-Button-1>", self._show_menu)
        self.columnconfigure(0, weight=1)

    def _show_menu(self, event: tk.Event) -> None:
        self.menu.tk_popup(event.x_root, event.y_root)
