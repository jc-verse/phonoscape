import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ..state import WindowState
from ..data.spectra import get_cursor_spectra


class CursorSpectView(QWidget):
    def __init__(self, parent: QWidget, state: WindowState):
        super().__init__(parent)

        self.state = state
        self.legend_artist = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        width = parent.width() if parent.width() > 1 else 600
        height = parent.height() if parent.height() > 1 else 400
        dpi = self.screen().logicalDotsPerInch()

        self.figure = Figure(figsize=(width / dpi, height / dpi), dpi=dpi, frameon=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas)

        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel("Hz", color=plt.rcParams["text.color"])
        self.ax.set_ylabel("dB", color=plt.rcParams["text.color"])

        self.ax.tick_params(
            axis="both", colors=plt.rcParams["text.color"], which="both"
        )

        for spine in self.ax.spines.values():
            spine.set_color(plt.rcParams["text.color"])

        self.ax.grid(True, color=(0.28, 0.28, 0.28), linewidth=0.5, alpha=0.65)

        self.lpc_artist = self.ax.plot(
            [], [], color="white", linewidth=0.8, label="LPC"
        )[0]
        self.dft_artist = self.ax.plot(
            [], [], color="cyan", linewidth=0.8, label="DFT"
        )[0]

        if self.state.selected_value.audio_traj is not None:
            self._update_spectrum_data()
        self.ax.relim(visible_only=True)
        self.ax.autoscale(axis="y")

        self.figure.tight_layout()
        self.canvas.draw_idle()

    def update_plot(
        self,
        data: bool = False,
        cursor: bool = False,
        xlim: bool = False,
        ylim: bool = False,
    ) -> None:
        if self.state.selected_value.audio_traj is None:
            return

        if data or cursor:
            self._update_spectrum_data()

        if xlim:
            self.ax.set_xlim(0, self._spectral_cutoff_hz())

        if ylim:
            self.ax.relim(visible_only=True)
            self.ax.autoscale(axis="y")

        if data or cursor or xlim or ylim:
            self.canvas.draw_idle()

    def _update_spectrum_data(self) -> None:
        spectra = get_cursor_spectra(self.state)

        if spectra.lpc_db is None:
            self.lpc_artist.set_data([], [])
            self.lpc_artist.set_visible(False)
        else:
            self.lpc_artist.set_data(spectra.frequency_hz, spectra.lpc_db)
            self.lpc_artist.set_visible(True)

        if spectra.dft_db is None:
            self.dft_artist.set_data([], [])
            self.dft_artist.set_visible(False)
        else:
            self.dft_artist.set_data(spectra.frequency_hz, spectra.dft_db)
            self.dft_artist.set_visible(True)

        self.ax.set_xlim(0, self._spectral_cutoff_hz())
        self._expand_y_if_needed(spectra.lpc_db, spectra.dft_db)

        visible_artists = [
            artist
            for artist in (self.lpc_artist, self.dft_artist)
            if artist.get_visible() and len(artist.get_xdata()) > 1
        ]

        if self.legend_artist is not None:
            self.legend_artist.remove()
            self.legend_artist = None

        if len(visible_artists) <= 1:
            return

        self.legend_artist = self.ax.legend(handles=visible_artists, loc="upper right")

        for text in self.legend_artist.get_texts():
            text.set_color("white")

    def _expand_y_if_needed(self, *spectra: np.ndarray | None) -> None:
        ymin, ymax = self.ax.get_ylim()
        changed = False

        for spectrum in spectra:
            if spectrum is None or spectrum.size == 0:
                continue

            y = spectrum[np.isfinite(spectrum)]

            if y.size == 0:
                continue

            if np.min(y) < ymin:
                ymin = float(np.min(y) - 10.0)
                changed = True

            if np.max(y) > ymax:
                ymax = float(np.max(y) + 10.0)
                changed = True

        if changed:
            self.ax.set_ylim(ymin, ymax)

    def _spectral_cutoff_hz(self) -> float:
        audio = self.state.selected_value.audio_traj
        cutoff_hz = self.state.app_config.spectral_display_cutoff_hz

        if audio is None:
            return cutoff_hz

        return min(cutoff_hz, audio.sample_rate_hz / 2.0)
