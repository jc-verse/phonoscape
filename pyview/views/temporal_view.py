from typing import Callable, cast, Any, Literal

import tkinter as tk
from tkinter import ttk

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.axes as plt_axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.image import AxesImage
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ..state import PyViewState, TrajDisplay, ScalarTrajDisplay, SpatialTrajDisplay
from ..data.process import get_plotting_data

ArtistType = (
    tuple[Literal["spatial"], list[Line2D]]
    | tuple[Literal["image"], AxesImage]
    | tuple[Literal["scalar"], Line2D]
)


class TemporalView(ttk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        state_model: PyViewState,
        *,
        on_cursor_change: Callable[[], None],
    ):
        super().__init__(parent)

        self._on_cursor_change = on_cursor_change
        self.dragging: (
            Literal["cursor", "head", "tail", None] | tuple[Literal["frame"], float]
        ) = None
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
        self.canvas.mpl_connect("figure_leave_event", self._on_figure_leave)

        self.reset_plot()

    def reset_plot(self) -> None:
        self.figure.clear()
        self.figure.subplots_adjust(
            left=0.01, right=0.99, top=0.99, bottom=0.01, hspace=0
        )
        n = len(self.state_model.config.temporal_disp_specs)
        height_ratios = [1.0, 0.08] + [  # Framing trajectory and spacing
            1.0 if spec.content != "SPECT" else 2.0
            for spec in self.state_model.config.temporal_disp_specs
        ]
        gs = self.figure.add_gridspec(
            nrows=len(height_ratios), ncols=1, height_ratios=height_ratios
        )
        self.axes = [self.figure.add_subplot(gs[0])] + [
            self.figure.add_subplot(gs[i + 2]) for i in range(n)
        ]

        self._refresh_plotting_data()

        duration_s = self.state_model.selected_value.duration_s
        self.artists: list[ArtistType] = []
        self.zero_artists: list[Line2D | None] = []
        self.cursor_artists: list[Line2D] = []
        for i, ax, spec in zip(range(n + 1), self.axes, self._get_temp_disp_specs()):
            artist, zero_artist, cursor_artist = self._plot_one_axis(
                ax, spec, i=i, duration_s=duration_s
            )
            self.artists.append(artist)
            self.zero_artists.append(zero_artist)
            self.cursor_artists.append(cursor_artist)

        self.canvas.draw_idle()

    def update_plot(
        self,
        cursor: bool = False,
        trajectories: bool = False,
        variable: bool = False,
        frame: bool = False,
    ) -> None:
        if cursor:
            for line in self.cursor_artists:
                line.set_xdata([self.state_model.cursor_s, self.state_model.cursor_s])
        if variable:
            trajectories = True
            frame = True
            self._refresh_plotting_data()
        if trajectories:
            for i, artist in enumerate(self.artists):
                t, data = self.plotting_data[i]
                if artist[0] == "image":
                    artist[1].set_data(data)
                    artist[1].set_extent(t)
                elif artist[0] == "spatial":
                    for j in range(data.shape[1]):
                        artist[1][j].set_data(t, data[:, j])
                elif artist[0] == "scalar":
                    artist[1].set_data(t, data)
                if artist := self.zero_artists[i]:
                    artist.set_visible(False)
                ax = self.axes[i]
                ax.relim(visible_only=True)
                ax.autoscale(axis="y")
                if i == 0:
                    ax.set_xlim(0, self.state_model.selected_value.duration_s)
                if artist := self.zero_artists[i]:
                    ymin, ymax = ax.get_ylim()
                    zero_visible = ymin < 0 < ymax
                    artist.set_visible(zero_visible)
        if frame:
            head_s = self.state_model.head_s
            tail_s = self.state_model.tail_s
            for i, ax in enumerate(self.axes):
                if i > 0:
                    ax.set_xlim(head_s, tail_s)
            ymin, ymax = self.axes[0].get_ylim()
            self.frame_artist.set_verts(
                [
                    [
                        (head_s, ymin),
                        (head_s, ymax),
                        (tail_s, ymax),
                        (tail_s, ymin),
                        (head_s, ymin),
                    ]
                ]
            )
        if cursor or trajectories or frame:
            self.canvas.draw_idle()

    def _plot_one_axis(
        self, ax: plt_axes.Axes, spec: TrajDisplay, i: int, duration_s: float
    ):
        traj = self.state_model.selected_value.trajectories[spec.traj_name]
        t, data = self.plotting_data[i]
        artist: ArtistType | None = None
        if isinstance(spec, SpatialTrajDisplay):
            artist = ("spatial", [])
            for j in range(data.shape[1]):
                a = ax.plot(
                    t,
                    data[:, j],
                    linewidth=0.8,
                    label=spec.components[j],
                    color=traj.color,
                    alpha=(1 - j * 0.3),
                )[0]
                artist[1].append(a)

            if len(spec.components) > 1:
                ax.legend(
                    loc="upper right",
                    frameon=True,
                    borderpad=0.2,
                    handlelength=1.2,
                    handletextpad=0.3,
                )
        elif spec.content == "SPECT":
            artist = (
                "image",
                ax.imshow(
                    data,
                    aspect="auto",
                    origin="lower",
                    extent=t,
                    cmap="gray_r",
                ),
            )
        elif spec.content in (
            "SIGNAL",
            "VEL",
            "ABSVEL",
            "RMS",
            "ZC",
        ):
            artist = ("scalar", ax.plot(t, data, linewidth=0.8, color=traj.color)[0])
        else:
            raise ValueError(
                f"Unexpected content type for temporal display: {spec.content}"
            )

        # No label for framing trajectory
        if i > 0:
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

        ax.set_xlim(0, duration_s)

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
            # Reset limits because invisible line still affects autoscaling
            ax.relim(visible_only=True)
            ax.autoscale(axis="y")
        else:
            zero_artist = None

        cursor_artist = ax.axvline(
            self.state_model.cursor_s,
            color=plt.rcParams["text.color"],
            linewidth=0.5,
            zorder=1000,
            clip_on=True,
        )

        if i == 0:
            ymin, ymax = ax.get_ylim()
            self.frame_artist = ax.fill_betweenx(
                [ymin, ymax],
                self.state_model.head_s,
                self.state_model.tail_s,
                color=plt.rcParams["text.color"],
                alpha=0.3,
                zorder=1000,
                clip_on=True,
            )

        return artist, zero_artist, cursor_artist

    def _get_temp_disp_specs(self):
        framing_traj_name = self.state_model.config.framing_traj
        framing_traj = self.state_model.selected_value.trajectories[framing_traj_name]
        framing_traj_spec = (
            ScalarTrajDisplay(content="SIGNAL", traj_name=framing_traj_name)
            if framing_traj.kind == "scalar"
            else SpatialTrajDisplay(
                content="movement",
                traj_name=framing_traj_name,
                traj_dims=self.state_model.dimensions,
                components=["x", "y", "z"][:self.state_model.dimensions],
            )
        )
        return [framing_traj_spec] + self.state_model.config.temporal_disp_specs

    def _refresh_plotting_data(self) -> None:
        self.plotting_data = [
            (
                get_plotting_data(
                    self.state_model.selected_value.trajectories[spec.traj_name],
                    spec,
                    self.state_model.dimensions,
                )
                if spec.traj_name != self.state_model.config.audio_traj
                or spec.content != "SPECT"
                else cast(tuple[Any, np.ndarray], self.state_model.audio_spect)
            )
            for spec in self._get_temp_disp_specs()
        ]

    def _event_is_in_cursor_axes(self, event) -> bool:
        return event.inaxes in self.axes and event.inaxes != self.axes[0]

    def _event_is_in_frame_axes(self, event) -> bool:
        return event.inaxes == self.axes[0]

    def _toolbar_is_active(self) -> bool:
        toolbar = getattr(self.canvas, "toolbar", None)
        return toolbar is not None and bool(getattr(toolbar, "mode", ""))

    def _on_press(self, event) -> None:
        if event.button != 1 or self._toolbar_is_active() or event.xdata is None:
            return
        if self._event_is_in_cursor_axes(event):
            self.dragging = "cursor"
            self.state_model.cursor_s = float(event.xdata)
            self.update_plot(cursor=True)
            self._on_cursor_change()
        elif self._event_is_in_frame_axes(event):
            loc = float(event.xdata)
            dist_to_head = abs(loc - self.state_model.head_s)
            dist_to_tail = abs(loc - self.state_model.tail_s)
            thres_dist = (
                self.state_model.min_sel_dur_s
                * self.state_model.selected_value.duration_s
            )
            if dist_to_head < dist_to_tail and dist_to_head < thres_dist:
                self.dragging = "head"
                self.state_model.head_s = loc
                self.update_plot(frame=True)
            elif dist_to_tail < dist_to_head and dist_to_tail < thres_dist:
                self.dragging = "tail"
                self.state_model.tail_s = loc
                self.update_plot(frame=True)
            elif self.state_model.head_s < loc < self.state_model.tail_s:
                self.dragging = ("frame", loc)

    def _on_motion(self, event) -> None:
        if not self.dragging or event.xdata is None:
            return
        if self.dragging == "cursor":
            if self._event_is_in_cursor_axes(event):
                self.state_model.cursor_s = float(event.xdata)
                self.update_plot(cursor=True)
                self._on_cursor_change()
            else:
                # Cancel drag if moved outside of axes
                self.dragging = None
        elif self.dragging == "head":
            if self._event_is_in_frame_axes(event):
                loc = min(
                    float(event.xdata),
                    self.state_model.tail_s - self.state_model.min_sel_dur_s,
                )
                self.state_model.head_s = loc
                self.update_plot(frame=True)
            else:
                self.dragging = None
        elif self.dragging == "tail":
            if self._event_is_in_frame_axes(event):
                loc = max(
                    float(event.xdata),
                    self.state_model.head_s + self.state_model.min_sel_dur_s,
                )
                self.state_model.tail_s = loc
                self.update_plot(frame=True)
            else:
                self.dragging = None
        else:
            old_loc = self.dragging[1]
            if self._event_is_in_frame_axes(event):
                loc = float(event.xdata)
                delta = loc - old_loc
                if self.state_model.head_s + delta < 0:
                    delta = -self.state_model.head_s
                elif (
                    self.state_model.tail_s + delta
                    > self.state_model.selected_value.duration_s
                ):
                    delta = (
                        self.state_model.selected_value.duration_s
                        - self.state_model.tail_s
                    )
                self.state_model.head_s += delta
                self.state_model.tail_s += delta
                self.update_plot(frame=True)
                self.dragging = ("frame", loc)
            else:
                self.dragging = None

    def _on_release(self, event) -> None:
        self.dragging = None

    def _on_figure_leave(self, event) -> None:
        self.dragging = None
