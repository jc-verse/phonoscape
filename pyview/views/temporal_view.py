from typing import Callable

import numpy as np
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
import matplotlib.axes as plt_axes

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ..state import Trajectory, PyViewState


class TemporalView(ttk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        state_model: PyViewState,
        *,
        on_cursor_changed: Callable[[float], None],
    ):
        super().__init__(parent)

        self._on_cursor_changed = on_cursor_changed
        self._cursor_dragging = False
        self._cursor_lines = []
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

    def plot(self) -> None:
        self.figure.clear()

        variable = self.state_model.selected_value

        self.figure.subplots_adjust(
            left=0.01, right=0.99, top=0.99, bottom=0.01, hspace=0
        )
        n = len(self.state_model.temporal_map)

        self.height_ratios = [1.0] * n
        self.gs = self.figure.add_gridspec(
            nrows=n, ncols=1, height_ratios=self.height_ratios
        )
        axes = [self.figure.add_subplot(self.gs[i, 0]) for i in range(n)]

        for i, (ax, traj) in enumerate(zip(axes, self.state_model.temporal_map)):
            self._plot_one_axis(ax, traj, i=i, duration=variable.duration_ms)

        self._cursor_lines = []
        self.set_cursor(self.state_model.cursor_s, notify=False)
        self.canvas.draw_idle()

    def set_cursor(self, t: float, *, notify: bool = True) -> None:
        axes = self._temporal_axes()
        if not axes:
            return

        xmin, xmax = axes[0].get_xlim()
        if xmin > xmax:
            xmin, xmax = xmax, xmin

        t = max(xmin, min(xmax, t))

        if len(self._cursor_lines) != len(axes):
            for line in self._cursor_lines:
                try:
                    line.remove()
                except ValueError:
                    pass

            self._cursor_lines = [
                ax.axvline(
                    t,
                    color=plt.rcParams["text.color"],
                    linewidth=0.5,
                    zorder=1000,
                    clip_on=True,
                )
                for ax in axes
            ]
        else:
            for line in self._cursor_lines:
                line.set_xdata([t, t])

        self.canvas.draw_idle()

        if notify:
            self._on_cursor_changed(t)

    def _plot_one_axis(
        self, ax: plt_axes.Axes, name: str, i: int, duration: float
    ) -> None:
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
        t = np.arange(traj.n_samples) / traj.sample_rate_hz
        if is_spect:
            self.height_ratios[i] = 4.0
            self.gs.set_height_ratios(self.height_ratios)
            ax.specgram(
                traj.data,
                NFFT=1024,
                Fs=traj.sample_rate_hz,
                noverlap=512,
                cmap="gray_r",
            )
        elif traj.kind == "scalar":
            ax.plot(t, traj.data, linewidth=0.8, color=traj.color)
        else:
            labels = ["x", "y", "z"]
            for i in range(min(3, traj.dimensions)):
                ax.plot(
                    t,
                    traj.data[:, i],
                    linewidth=0.8,
                    label=labels[i],
                    color=traj.color,
                    alpha=(1 - i * 0.3),
                )

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

    def _temporal_axes(self):
        return [ax for ax in self.figure.axes if ax.get_visible()]

    def _event_is_in_temporal_axes(self, event) -> bool:
        return event.inaxes in self._temporal_axes()

    def _toolbar_is_active(self) -> bool:
        toolbar = getattr(self.canvas, "toolbar", None)
        return toolbar is not None and bool(getattr(toolbar, "mode", ""))

    def _on_press(self, event) -> None:
        if event.button != 1:
            return

        if self._toolbar_is_active():
            return

        if event.xdata is None or not self._event_is_in_temporal_axes(event):
            return

        self._cursor_dragging = True
        self.set_cursor(float(event.xdata))

    def _on_motion(self, event) -> None:
        if not self._cursor_dragging:
            return

        if event.xdata is None or not self._event_is_in_temporal_axes(event):
            return

        self.set_cursor(float(event.xdata))

    def _on_release(self, event) -> None:
        if not self._cursor_dragging:
            return

        self._cursor_dragging = False

        if event.xdata is not None and self._event_is_in_temporal_axes(event):
            self.set_cursor(float(event.xdata))
