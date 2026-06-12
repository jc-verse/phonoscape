import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QWidget, QVBoxLayout

from ..state import WindowState


class FreqDomainView(QWidget):
    def __init__(self, parent: QWidget, state: WindowState):
        super().__init__(parent)

        self.state = state

        layout = QVBoxLayout(self)
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
        f, spect_slice = self._get_current_spect()

        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.curve_artist = self.ax.plot(
            f, spect_slice, color=plt.rcParams["text.color"], linewidth=0.8
        )[0]
        self.ax.set_xlabel("Hz")
        self.ax.set_ylabel("dB")
        self.ax.set_ylim(
            self.state.selected_value.audio_traj.spect.min() - 5,
            self.state.selected_value.audio_traj.spect.max() + 5,
        )
        self.ax.set_xlim(0, self.state.app_config.spectral_display_cutoff_hz)
        # TODO: right/double/modified clicking gesture (open new window)

        self.canvas.draw_idle()

    def update_plot(
        self, data: bool = False, cursor: bool = False, xlim: bool = False
    ) -> None:
        assert self.state.selected_value.audio_traj is not None
        if data:
            self.ax.set_ylim(
                self.state.selected_value.audio_traj.spect.min() - 5,
                self.state.selected_value.audio_traj.spect.max() + 5,
            )

        if cursor or data:
            f, spect_slice = self._get_current_spect()
            self.curve_artist.set_data(f, spect_slice)

        if xlim:
            self.ax.set_xlim(0, self.state.app_config.spectral_display_cutoff_hz)

        if data or cursor or xlim:
            self.canvas.draw_idle()

    def _get_current_spect(self):
        assert self.state.selected_value.audio_traj is not None

        config = self.state.app_config
        audio_traj = self.state.selected_value.audio_traj
        spect_db = audio_traj.spect

        hop_s = config.overlap_ms * config.spectrogram_bandwidth_mode.value / 1000.0
        frame_idx = int(np.floor(self.state.cursor_s / hop_s + 0.5))
        frame_idx = max(0, min(frame_idx, spect_db.shape[1] - 1))

        f = (
            np.arange(spect_db.shape[0])
            * audio_traj.sample_rate_hz
            / (2 * config.fft_eval_points)
        )

        return f, spect_db[:, frame_idx]
