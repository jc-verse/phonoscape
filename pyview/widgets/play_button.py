import sounddevice as sd
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QMenu, QPushButton, QWidget
from PySide6.QtGui import QAction, QActionGroup

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
        half_window = round(0.15 * traj.sample_rate_hz / 2)
        start = max(head_index, cursor_index - half_window)
        end = min(tail_index, cursor_index + half_window)
        play_data = traj.data[start:end]
    else:
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

        self.menu = QMenu(self)
        self.action_group = QActionGroup(self)
        self.action_group.setExclusive(True)

        current_mode = self.state_model.play_mode.get()

        for mode in modes:
            action = QAction(mode, self)
            action.setCheckable(True)
            action.setChecked(mode == current_mode)
            action.triggered.connect(
                lambda checked=False, mode=mode: self.state_model.play_mode.set(mode)
            )
            self.action_group.addAction(action)
            self.menu.addAction(action)

        self.btn = QPushButton("Play", self)
        self.btn.clicked.connect(lambda: play(self.state_model))
        self.btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.btn.customContextMenuRequested.connect(self._show_menu)

        layout.addWidget(self.btn, 0, 0)

    def _show_menu(self, pos: QPoint) -> None:
        self.menu.popup(self.btn.mapToGlobal(pos))
