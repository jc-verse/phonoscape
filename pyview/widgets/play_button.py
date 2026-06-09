import sounddevice as sd
from PySide6.QtWidgets import QFrame, QGridLayout, QPushButton, QWidget

from ..state import WindowState

modes = (
    "Selection",
    "Entire file",
    "To cursor",
    "From cursor",
    "150ms @ cursor",
    "Between labels",
)


def play(state: WindowState) -> None:
    audio_traj = state.app_config.audio_traj
    if audio_traj is None:
        print("No audio trajectory configured.")
        return
    traj = state.selected_value.trajectories[audio_traj]
    play_data = None
    head_index = round(state.head_s * traj.sample_rate_hz)
    cursor_index = round(state.cursor_s * traj.sample_rate_hz)
    tail_index = round(state.tail_s * traj.sample_rate_hz)
    match state.play_mode:
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
        case "Between labels":
            labels = sorted(state.labels, key=lambda lbl: lbl.offset_s)
            if len(labels) < 2:
                return
            for left, right in zip(labels, labels[1:]):
                if left.offset_s <= state.cursor_s <= right.offset_s:
                    left_index = round(left.offset_s * traj.sample_rate_hz)
                    right_index = round(right.offset_s * traj.sample_rate_hz)
                    play_data = traj.data[left_index:right_index]
                    break
        case mode:
            print(f"Unknown play mode: {mode}")
            return

    if play_data is not None and len(play_data) > 0:
        sd.play(play_data, samplerate=traj.sample_rate_hz)


class PlayButton(QFrame):
    def __init__(
        self,
        parent: QWidget,
        state: WindowState,
    ):
        super().__init__(parent)

        self.state = state

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.btn = QPushButton("Play", self)
        self.btn.clicked.connect(lambda: play(self.state))

        layout.addWidget(self.btn, 0, 0)
