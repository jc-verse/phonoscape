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

        self.spectrum_artists = {
            "lpc_db": self.ax.plot([], [], linewidth=0.8, label="LPC")[0],
            "dft_db": self.ax.plot([], [], linewidth=0.8, label="DFT")[0],
            "avg_db": self.ax.plot([], [], linewidth=0.8, label="AVG")[0],
            "ceps_db": self.ax.plot([], [], linewidth=0.8, label="CEPS")[0],
        }

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
        visible_spectra = []

        for field_name, artist in self.spectrum_artists.items():
            spectrum = getattr(spectra, field_name, None)

            if spectrum is None:
                artist.set_data([], [])
                artist.set_visible(False)
                continue

            artist.set_data(spectra.frequency_hz, spectrum)
            artist.set_visible(True)
            visible_spectra.append(spectrum)

        self.ax.set_xlim(0, self._spectral_cutoff_hz())
        self._expand_y_if_needed(*visible_spectra)

        visible_artists = [
            artist
            for artist in self.spectrum_artists.values()
            if artist.get_visible() and len(artist.get_xdata()) > 1
        ]

        prop_cycle = plt.rcParams["axes.prop_cycle"]
        colors = [plt.rcParams["text.color"]] + prop_cycle.by_key()["color"]
        for i, artist in enumerate(visible_artists):
            artist.set_color(colors[i])

        if self.legend_artist is not None:
            self.legend_artist.remove()
            self.legend_artist = None

        if len(visible_artists) <= 1:
            return

        self.legend_artist = self.ax.legend(
            handles=visible_artists, loc="upper right", frameon=False
        )

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
