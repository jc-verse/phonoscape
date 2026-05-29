from typing import Callable

import numpy as np
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
import matplotlib.axes as plt_axes

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ..state import PyViewState


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
        n = len(self.state_model.temporal_map)
        self.height_ratios = [1.0] * n
        self.gs = self.figure.add_gridspec(
            nrows=n, ncols=1, height_ratios=self.height_ratios
        )
        self.axes = [self.figure.add_subplot(self.gs[i, 0]) for i in range(n)]

        duration = self.state_model.selected_value.duration_ms
        self.artists = []
        for i, (ax, traj) in enumerate(zip(self.axes, self.state_model.temporal_map)):
            artist = self._plot_one_axis(ax, traj, i=i, duration=duration)
            self.artists.append(artist)

        self.cursor_artists = [
            ax.axvline(
                self.state_model.cursor_s,
                color=plt.rcParams["text.color"],
                linewidth=0.5,
                zorder=1000,
                clip_on=True,
            )
            for ax in self.axes
        ]

    def update_plot(self, cursor: bool = False, trajectories: bool = False) -> None:
        if cursor:
            for line in self.cursor_artists:
                line.set_xdata([self.state_model.cursor_s, self.state_model.cursor_s])
        if trajectories:
            duration = self.state_model.selected_value.duration_ms
            for i, traj in enumerate(self.state_model.temporal_map):
                traj, is_spect = self._get_traj(traj)
                t = np.arange(traj.n_samples) / traj.sample_rate_hz
                artist = self.artists[i]
                if is_spect:
                    # TODO: incremental update (require separate spectrogram computation)
                    self.artists[i] = self.axes[i].specgram(
                        traj.data,
                        NFFT=1024,
                        Fs=traj.sample_rate_hz,
                        noverlap=512,
                        cmap="gray_r",
                    )
                elif traj.kind == "scalar":
                    artist.set_data(t, traj.data)
                else:
                    for j in range(min(3, traj.dimensions)):
                        artist[j].set_data(t, traj.data[:, j])
                self.axes[i].relim()
                self.axes[i].autoscale_view(scalex=False, scaley=True)
                self.axes[i].set_xlim(0, duration)
        if cursor or trajectories:
            self.canvas.draw_idle()

    def _plot_one_axis(
        self, ax: plt_axes.Axes, name: str, i: int, duration: float
    ):
        traj, is_spect = self._get_traj(name)
        t = np.arange(traj.n_samples) / traj.sample_rate_hz
        artist = None
        if is_spect:
            self.height_ratios[i] = 4.0
            self.gs.set_height_ratios(self.height_ratios)
            artist = ax.specgram(
                traj.data,
                NFFT=1024,
                Fs=traj.sample_rate_hz,
                noverlap=512,
                cmap="gray_r",
            )
        elif traj.kind == "scalar":
            artist = ax.plot(t, traj.data, linewidth=0.8, color=traj.color)[0]
        else:
            labels = ["x", "y", "z"]
            artist = []
            for i in range(min(3, traj.dimensions)):
                a = ax.plot(
                    t,
                    traj.data[:, i],
                    linewidth=0.8,
                    label=labels[i],
                    color=traj.color,
                    alpha=(1 - i * 0.3),
                )[0]
                artist.append(a)

            ax.legend(
                loc="upper right",
                frameon=True,
                borderpad=0.2,
                handlelength=1.2,
                handletextpad=0.3,
            )

        ax.text(
            0.01,
            0.98,
            f"{traj.name}  {traj.sample_rate_hz:.0f} Hz",
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
        
        return artist

    def _get_traj(self, name: str):
        candidate_names = [name, name.upper(), name.lower()]
        traj = None
        is_spect = False
        for candidate in candidate_names:
            if candidate in self.state_model.selected_value.trajectories:
                traj = self.state_model.selected_value.trajectories[candidate]
                break
        else:
            if name.lower().endswith("_spect"):
                base_name = name[:-6]
                for candidate in [base_name, base_name.upper(), base_name.lower()]:
                    if candidate in self.state_model.selected_value.trajectories:
                        traj = self.state_model.selected_value.trajectories[candidate]
                        break
                else:
                    raise ValueError(
                        f"Trajectory '{base_name}' (requested via '{name}') not found among variable trajectories"
                    )
                if traj.kind != "scalar":
                    raise ValueError(
                        f"Trajectory '{traj.name}' found for '{name}' is not scalar and thus cannot be spectrogrammed"
                    )
                is_spect = True

            else:
                raise ValueError(
                    f"Trajectory '{name}' not found among variable trajectories"
                )
        return traj, is_spect

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
