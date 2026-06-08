import sounddevice as sd
from PySide6.QtWidgets import QFrame, QGridLayout, QPushButton, QWidget

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
    head_index = round(state_model.head_s * traj.sample_rate_hz)
    cursor_index = round(state_model.cursor_s * traj.sample_rate_hz)
    tail_index = round(state_model.tail_s * traj.sample_rate_hz)
    match state_model.play_mode:
        case "Selection":
            play_data = traj.data[head_index:tail_index]
        case "Entire file":
            play_data = traj.data
        case "To cursor":
            play_data = (
                traj.data[head_index:cursor_index]
                if cursor_index > head_index
                else traj.data[head_index:tail_index]
            )
        case "From cursor":
            play_data = (
                traj.data[cursor_index:tail_index]
                if cursor_index < tail_index
                else traj.data[head_index:tail_index]
            )
        case "150ms @ cursor":
            half_window = round(0.15 * traj.sample_rate_hz / 2)
            start = max(head_index, cursor_index - half_window)
            end = min(tail_index, cursor_index + half_window)
            play_data = traj.data[start:end]
        case mode:
            print(f"Unknown play mode: {mode}")
            return

    if play_data is not None and len(play_data) > 0:
        sd.play(play_data, samplerate=traj.sample_rate_hz)


class PlayButton(QFrame):
    def __init__(
        self,
        parent: QWidget,
        state_model: PyViewState,
    ):
        super().__init__(parent)

        self.state_model = state_model

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.btn = QPushButton("Play", self)
        self.btn.clicked.connect(lambda: play(self.state_model))

        layout.addWidget(self.btn, 0, 0)
