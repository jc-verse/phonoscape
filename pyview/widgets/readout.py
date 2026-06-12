from numpy.typing import NDArray

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget

from ..state import WindowState, TrajDisplay, SpatialTrajDisplay


class Readout(QFrame):
    def __init__(self, parent: QWidget, state: WindowState):
        super().__init__(parent)

        self.state = state

        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label.setCursor(Qt.CursorShape.IBeamCursor)
        self.label.setStyleSheet("font-size: 16px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.label)

    def readout_traj(self, traj_spec: TrajDisplay, data: NDArray, time_s: float):
        traj = self.state.selected_value.trajectories[traj_spec.traj_name]
        idx = round(time_s * traj.sample_rate_hz)
        idx = max(0, min(idx, traj.n_samples - 1))

        if isinstance(traj_spec, SpatialTrajDisplay):
            traj_value = "\n".join(
                f"{name} = {value:.2f}"
                for name, value in zip(traj_spec.components, data[idx])
            )
        elif traj_spec.content != "SPECT":
            traj_value = f"{data[idx]:.2f}"
        else:
            traj_value = ""

        value_str = f"{traj_spec} @ {time_s * 1000:.1f} ms\n{traj_value}"
        self.label.setText(value_str)

    def readout_camera(self, elev: float, azim: float, roll: float):
        value_str = f"Camera angle\nazim={azim:.1f}°\nelev={elev:.1f}°\nroll={roll:.1f}°"
        self.label.setText(value_str)

    def readout_fps(self, cycle_mode: str, elapsed_s: float, playback_rate: float):
        value_str = f"Cycle mode: {cycle_mode}\nFPS: {1 / elapsed_s:.1f}\nPlayback rate: {playback_rate:.1f}x\nNudge step: {elapsed_s * playback_rate * 1000:.1f} ms"
        self.label.setText(value_str)

    def clear_readout(self):
        self.label.clear()
