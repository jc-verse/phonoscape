import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ..state import WindowState
from ..data.spectra import get_cursor_spectra


class CursorSpectView(QWidget):
    def __init__(self, parent: QWidget, state: WindowState):
        super().__init__(parent)

        self.state = state
        self.legend = None

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
        self._style_axis()

        self.lpc_artist = self.ax.plot(
            [], [], color="white", linewidth=0.8, label="LPC"
        )[0]
        self.dft_artist = self.ax.plot(
            [], [], color="cyan", linewidth=0.8, label="DFT"
        )[0]

        if self.state.selected_value.audio_traj is not None:
            self._update_spectrum_data()

        self.figure.tight_layout()
        self.canvas.draw_idle()

    def update_plot(
        self, data: bool = False, cursor: bool = False, xlim: bool = False
    ) -> None:
        if self.state.selected_value.audio_traj is None:
            return

        if data or cursor:
            self._update_spectrum_data()

        if xlim:
            self.ax.set_xlim(0, self._spectral_cutoff_hz())

        if data or cursor or xlim:
            self.canvas.draw_idle()

    def _style_axis(self) -> None:
        self.figure.patch.set_facecolor("black")
        self.ax.set_facecolor("black")
        self.ax.set_xlabel("Hz", color="white")
        self.ax.set_ylabel("dB", color="white")
        self.ax.set_xlim(0, self._spectral_cutoff_hz())
        self.ax.set_ylim(-20, 0)

        self.ax.tick_params(axis="both", colors="white", which="both")

        for spine in self.ax.spines.values():
            spine.set_color("white")

        self.ax.grid(True, color=(0.28, 0.28, 0.28), linewidth=0.5, alpha=0.65)

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
        self._update_legend()

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

    def _update_legend(self) -> None:
        visible_artists = [
            artist
            for artist in (self.lpc_artist, self.dft_artist)
            if artist.get_visible() and len(artist.get_xdata()) > 1
        ]

        if self.legend is not None:
            self.legend.remove()
            self.legend = None

        if len(visible_artists) <= 1:
            return

        self.legend = self.ax.legend(
            handles=visible_artists,
            loc="upper right",
            facecolor="black",
            edgecolor="white",
            framealpha=0.75,
        )

        for text in self.legend.get_texts():
            text.set_color("white")

    def _spectral_cutoff_hz(self) -> float:
        audio = self.state.selected_value.audio_traj
        cutoff_hz = self.state.app_config.spectral_display_cutoff_hz

        if audio is None:
            return cutoff_hz

        return min(cutoff_hz, audio.sample_rate_hz / 2.0)
