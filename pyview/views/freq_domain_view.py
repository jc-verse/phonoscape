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
        # TODO: double clicking gesture (open new window)

        self.canvas.draw_idle()

    def update_plot(self) -> None:
        assert self.state.selected_value.audio_traj is not None
        f, spect_slice = self._get_current_spect()

        self.curve_artist.set_data(f, spect_slice)
        self.ax.relim()
        self.ax.autoscale_view()

        self.canvas.draw_idle()

    def _get_current_spect(self):
        assert self.state.selected_value.audio_traj is not None
        delta_t = self.state.selected_value.audio_traj.spect_delta_t_s
        spect_db = self.state.selected_value.audio_traj.spect
        extent = self.state.selected_value.audio_traj.spect_extent
        frame_idx = round(self.state.cursor_s / delta_t)
        frame_idx = max(0, min(frame_idx, spect_db.shape[1] - 1))
        f = np.linspace(extent[2], extent[3], spect_db.shape[0])
        return f, spect_db[:, frame_idx]
