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


class SplitPlayButton(ttk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        state_model: PyViewState,
    ):
        super().__init__(parent, style="SplitButton.TFrame", padding=0)

        self.state_model = state_model
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
        mode = self.play_mode.get()
        audio_traj = self.state_model.config.audio_traj
        if audio_traj is None:
            print("No audio trajectory configured.")
            return
        traj = self.state_model.selected_value.trajectories[audio_traj]
        play_data = None
        head_index = int(self.state_model.head_s * traj.sample_rate_hz)
        cursor_index = int(self.state_model.cursor_s * traj.sample_rate_hz)
        tail_index = int(self.state_model.tail_s * traj.sample_rate_hz)
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
