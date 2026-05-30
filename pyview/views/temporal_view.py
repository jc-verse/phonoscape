from typing import Callable

import numpy as np
import tkinter as tk
from tkinter import ttk
from scipy.signal import ShortTimeFFT, windows

import matplotlib.pyplot as plt
import matplotlib.axes as plt_axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ..state import PyViewState, TrajDisplay


class TemporalView(ttk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        state_model: PyViewState,
        *,
        on_cursor_changed: Callable[[], None],
    ):
        super().__init__(parent)

        self._on_cursor_changed = on_cursor_changed
        self._cursor_dragging = False
        self.state_model = state_model
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.width = parent.winfo_width()
        self.height = parent.winfo_height()
        self.figure = Figure(
            figsize=(
                self.width / self.state_model.dpi,
                self.height / self.state_model.dpi,
            ),
            dpi=state_model.dpi,
        )
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky="nsew")

        self.canvas.mpl_connect("button_press_event", self._on_press)
        self.canvas.mpl_connect("motion_notify_event", self._on_motion)
        self.canvas.mpl_connect("button_release_event", self._on_release)

        self.reset_plot()

    def reset_plot(self) -> None:
        self.figure.clear()
        self.figure.subplots_adjust(
            left=0.01, right=0.99, top=0.99, bottom=0.01, hspace=0
        )
        n = len(self.state_model.config.temporal_disp_specs)
        height_ratios = [
            1.0 if spec.content != "SPECT" else 2.0
            for spec in self.state_model.config.temporal_disp_specs
        ]
        gs = self.figure.add_gridspec(nrows=n, ncols=1, height_ratios=height_ratios)
        self.axes = [self.figure.add_subplot(gs[i, 0]) for i in range(n)]

        self.plotting_data = [
            self._get_plotting_data(spec)
            for spec in self.state_model.config.temporal_disp_specs
        ]

        duration = self.state_model.selected_value.duration_ms
        self.artists = []
        self.zero_artists: list[Line2D | None] = []
        self.cursor_artists: list[Line2D] = []
        for i, ax, spec in zip(
            range(n), self.axes, self.state_model.config.temporal_disp_specs
        ):
            artist, zero_artist, cursor_artist = self._plot_one_axis(
                ax, spec, i=i, duration=duration
            )
            self.artists.append(artist)
            self.zero_artists.append(zero_artist)
            self.cursor_artists.append(cursor_artist)

    def update_plot(
        self, cursor: bool = False, trajectories: bool = False, variable: bool = False
    ) -> None:
        if cursor:
            for line in self.cursor_artists:
                line.set_xdata([self.state_model.cursor_s, self.state_model.cursor_s])
        if variable:
            trajectories = True
            self.plotting_data = [
                self._get_plotting_data(spec)
                for spec in self.state_model.config.temporal_disp_specs
            ]
        if trajectories:
            duration = self.state_model.selected_value.duration_ms
            for i, spec in enumerate(self.state_model.config.temporal_disp_specs):
                t, data = self.plotting_data[i]
                artist = self.artists[i]
                if spec.content == "SPECT":
                    self.artists[i].set_data(data)
                    self.artists[i].set_extent(t)
                elif spec.content in ("SIGNAL", "velocity", "acceleration"):
                    artist.set_data(t, data)
                elif spec.content == "movement":
                    for j in range(data.shape[1]):
                        artist[j].set_data(t, data[:, j])
                if artist := self.zero_artists[i]:
                    artist.set_visible(False)
                self.axes[i].relim()
                self.axes[i].autoscale_view(scalex=False, scaley=True)
                self.axes[i].set_xlim(0, duration)
                if artist := self.zero_artists[i]:
                    ymin, ymax = self.axes[i].get_ylim()
                    zero_visible = ymin < 0 < ymax
                    artist.set_visible(zero_visible)
        if cursor or trajectories:
            self.canvas.draw_idle()

    def _plot_one_axis(
        self, ax: plt_axes.Axes, spec: TrajDisplay, i: int, duration: float
    ):
        traj = self.state_model.selected_value.trajectories[spec.traj_name]
        t, data = self.plotting_data[i]
        artist = None
        if spec.content == "SPECT":
            artist = ax.imshow(
                data,
                aspect="auto",
                origin="lower",
                extent=t,
                cmap="gray_r",
            )
        elif spec.content == "SIGNAL":
            artist = ax.plot(t, data, linewidth=0.8, color=traj.color)[0]
        elif spec.content == "movement":
            artist = []
            for j in range(data.shape[1]):
                a = ax.plot(
                    t,
                    data[:, j],
                    linewidth=0.8,
                    label=spec.components[j],
                    color=traj.color,
                    alpha=(1 - j * 0.3),
                )[0]
                artist.append(a)

            if len(spec.components) > 1:
                ax.legend(
                    loc="upper right",
                    frameon=True,
                    borderpad=0.2,
                    handlelength=1.2,
                    handletextpad=0.3,
                )
        elif spec.content in ("velocity", "acceleration"):
            artist = ax.plot(t, data, linewidth=0.8, color=traj.color)[0]
        else:
            raise ValueError(
                f"Unexpected content type for temporal display: {spec.content}"
            )

        ax.text(
            0.01,
            0.98,
            f"{spec}  {traj.sample_rate_hz:.0f} Hz",
            ha="left",
            va="top",
            transform=ax.transAxes,
            bbox=dict(
                facecolor=plt.rcParams["figure.facecolor"],
                alpha=0.65,
                edgecolor="none",
                pad=1,
            ),
        )

        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_title("")
        ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

        ax.set_xlim(0, duration)

        for spine in ax.spines.values():
            spine.set_visible(True)

        if spec.content != "SPECT":
            ymin, ymax = ax.get_ylim()
            zero_visible = ymin < 0 < ymax
            zero_artist = ax.axhline(
                0,
                linewidth=0.5,
                linestyle="--",
                color=plt.rcParams["text.color"],
                zorder=0,
                visible=zero_visible,
            )
        else:
            zero_artist = None

        cursor_artist = ax.axvline(
            self.state_model.cursor_s,
            color=plt.rcParams["text.color"],
            linewidth=0.5,
            zorder=1000,
            clip_on=True,
        )

        return artist, zero_artist, cursor_artist

    def _get_plotting_data(self, spec: TrajDisplay):
        traj = self.state_model.selected_value.trajectories[spec.traj_name]
        t = np.arange(traj.n_samples) / traj.sample_rate_hz
        if spec.content == "SPECT":
            window_ms = 25
            overlap = 0.75
            nperseg = round(traj.sample_rate_hz * window_ms / 1000)
            hop = max(1, round(nperseg * (1.0 - overlap)))

            win = windows.hann(nperseg, sym=False)

            stft = ShortTimeFFT(
                win=win,
                hop=hop,
                fs=traj.sample_rate_hz,
                mfft=1024,
                scale_to="magnitude",
            )

            S = stft.spectrogram(traj.data)
            S_db = 20 * np.log10(S + np.finfo(float).eps)
            extent = [0, t[-1], 0, traj.sample_rate_hz / 2]
            return extent, S_db
        elif spec.content == "SIGNAL":
            return t, traj.data
        elif spec.content == "movement":
            cols = [{"x": 0, "y": 1, "z": 2}[comp] for comp in spec.components]
            return t, traj.data[:, cols]
        elif spec.content == "velocity":
            cols = [{"x": 0, "y": 1, "z": 2}[comp] for comp in spec.components]
            ps = traj.data[:, cols]
            vs = np.gradient(ps, axis=0) * traj.sample_rate_hz
            if vs.shape[1] > 1:
                speed = np.linalg.norm(vs, axis=1)
            else:
                # Preserve sign for 1D
                # TODO: currently this way for mview compatibility, but I think
                # "velocity" and "speed" should be separate content types
                # Otherwise there's this inconsistency between 1D and multi-D
                speed = vs[:, 0]
            return t, speed
        elif spec.content == "acceleration":
            cols = [{"x": 0, "y": 1, "z": 2}[comp] for comp in spec.components]
            ps = traj.data[:, cols]
            vs = np.gradient(ps, axis=0) * traj.sample_rate_hz
            accs = np.gradient(vs, axis=0) * traj.sample_rate_hz
            if accs.shape[1] > 1:
                accel = np.linalg.norm(accs, axis=1)
            else:
                accel = accs[:, 0]
            return t, accel
        else:
            raise ValueError(
                f"Unexpected content type for temporal display: {spec.content}"
            )

    def _event_is_in_temporal_axes(self, event) -> bool:
        return event.inaxes in self.axes

    def _toolbar_is_active(self) -> bool:
        toolbar = getattr(self.canvas, "toolbar", None)
        return toolbar is not None and bool(getattr(toolbar, "mode", ""))

    def _on_press(self, event) -> None:
        if (
            event.button != 1
            or self._toolbar_is_active()
            or event.xdata is None
            or not self._event_is_in_temporal_axes(event)
        ):
            return

        self._cursor_dragging = True
        self.state_model.cursor_s = float(event.xdata)
        self.update_plot(cursor=True)
        self._on_cursor_changed()

    def _on_motion(self, event) -> None:
        if (
            not self._cursor_dragging
            or event.xdata is None
            or not self._event_is_in_temporal_axes(event)
        ):
            return

        self.state_model.cursor_s = float(event.xdata)
        self.update_plot(cursor=True)
        self._on_cursor_changed()

    def _on_release(self, event) -> None:
        if (
            not self._cursor_dragging
            or event.xdata is None
            or not self._event_is_in_temporal_axes(event)
        ):
            return
        self._cursor_dragging = False

        self.state_model.cursor_s = float(event.xdata)
        self.update_plot(cursor=True)
        self._on_cursor_changed()
