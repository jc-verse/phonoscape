import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QWidget, QVBoxLayout

from ..state import PyViewState


class FreqDomainView(QWidget):
    def __init__(self, parent: QWidget, state_model: PyViewState):
        super().__init__(parent)

        self.state_model = state_model

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

        if self.state_model.audio_spect is None:
            return
        f, spect = self._get_current_spect()

        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.curve_artist = self.ax.plot(
            f, spect, color=plt.rcParams["text.color"], linewidth=0.8
        )[0]
        self.ax.set_xlabel("Hz")
        self.ax.set_ylabel("dB")
        self.ax.set_ylim(
            self.state_model.audio_spect[1].min() - 5,
            self.state_model.audio_spect[1].max() + 5,
        )

        self.canvas.draw_idle()

    def update_plot(self) -> None:
        assert self.state_model.audio_spect is not None
        f, spect_db = self._get_current_spect()

        self.curve_artist.set_data(f, spect_db)
        self.ax.relim()
        self.ax.autoscale_view()

        self.canvas.draw_idle()

    def _get_current_spect(self):
        assert self.state_model.audio_spect is not None
        assert self.state_model.config.audio_traj is not None
        # This must be in sync with data.process.get_plotting_data for SPECT.
        # TODO: refactor to avoid this duplication.
        traj = self.state_model.data[self.state_model.selected_variable].trajectories[
            self.state_model.config.audio_traj
        ]
        window_ms = 25
        overlap = 0.75
        nperseg = round(traj.sample_rate_hz * window_ms / 1000)
        hop = max(1, round(nperseg * (1.0 - overlap)))
        delta_t = hop / traj.sample_rate_hz
        extent, spect_db = self.state_model.audio_spect
        frame_idx = round(self.state_model.cursor_s / delta_t)
        frame_idx = max(0, min(frame_idx, spect_db.shape[1] - 1))
        f = np.linspace(extent[2], extent[3], spect_db.shape[0])
        return f, spect_db[:, frame_idx]
