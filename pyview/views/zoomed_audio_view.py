import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QHBoxLayout, QWidget

from ..state import WindowState


class ZoomedAudioView(QWidget):
    def __init__(self, parent: QWidget, state: WindowState):
        super().__init__(parent)

        self.state = state

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # At construction time, Qt widgets often still report very small sizes.
        # Keep the old structure, but fall back to a reasonable initial figure size.
        width = parent.width() if parent.width() > 1 else 600
        height = parent.height() if parent.height() > 1 else 400
        dpi = self.screen().logicalDotsPerInch()

        self.figure = Figure(figsize=(width / dpi, height / dpi), dpi=dpi, frameon=True)
        self.figure.tight_layout()

        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas)

        if self.state.selected_value.audio_traj is None:
            return
        t, audio_slice = self._get_current_audio_slice()

        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.curve_artist = self.ax.plot(
            t, audio_slice, color=plt.rcParams["text.color"], linewidth=0.8
        )[0]
        self.cursor_artist = self.ax.axvline(
            0, color="green", linestyle="--", linewidth=0.8
        )
        self.ax.set_ylim(
            self.state.selected_value.audio_traj.signal.min(),
            self.state.selected_value.audio_traj.signal.max(),
        )
        self.ax.set_xlim(
            -self.state.app_config.analysis_window_ms / 2000,
            self.state.app_config.analysis_window_ms / 2000,
        )
        # TODO: right/double/modified clicking gesture (open new window)

        self.canvas.draw_idle()

    def update_plot(
        self, data: bool = False, cursor: bool = False, xlim: bool = False
    ) -> None:
        assert self.state.selected_value.audio_traj is not None
        if data:
            self.ax.set_ylim(
                self.state.selected_value.audio_traj.signal.min(),
                self.state.selected_value.audio_traj.signal.max(),
            )

        if xlim:
            self.ax.set_xlim(
                -self.state.app_config.analysis_window_ms / 2000,
                self.state.app_config.analysis_window_ms / 2000,
            )

        if data or cursor or xlim:
            t, audio_slice = self._get_current_audio_slice()
            self.curve_artist.set_data(t, audio_slice)

        if data or cursor or xlim:
            self.canvas.draw_idle()

    def _get_current_audio_slice(self):
        assert self.state.selected_value.audio_traj is not None

        config = self.state.app_config
        audio_traj = self.state.selected_value.audio_traj
        window_size_samples = round(
            config.analysis_window_ms * audio_traj.sample_rate_hz / 1000
        )
        center_sample = round(self.state.cursor_s * audio_traj.sample_rate_hz)
        start_sample = max(0, center_sample - window_size_samples // 2)
        end_sample = min(
            len(audio_traj.signal), center_sample + window_size_samples // 2
        )
        audio_slice = audio_traj.signal[start_sample:end_sample]
        t = (
            np.arange(start_sample, end_sample) / audio_traj.sample_rate_hz
            - self.state.cursor_s
        )
        return t, audio_slice
