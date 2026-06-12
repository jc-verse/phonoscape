from typing import cast, Literal

import numpy as np

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.collections import PathCollection, LineCollection
from matplotlib.lines import Line2D
from matplotlib.text import Text
from PySide6.QtWidgets import QWidget, QVBoxLayout

from ..state import WindowState
from ..data.process import compute_spline


class SpatialView2D(QWidget):
    def __init__(self, parent: QWidget, state: WindowState):
        super().__init__(parent)

        self.state = state
        self.history: bool | Literal["hue"] = False

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

        self.figure.clear()
        self.ax = self.figure.add_subplot(111)

        xmin, xmax, ymin, ymax = cast(
            tuple[float, float, float, float],
            self.state.app_config.spatial_bounds,
        )
        xmin -= (xmax - xmin) * 0.05
        xmax += (xmax - xmin) * 0.05
        ymin -= (ymax - ymin) * 0.05
        ymax += (ymax - ymin) * 0.05
        self.ax.set_xlim(xmin, xmax)
        self.ax.set_ylim(ymin, ymax)
        self.ax.set_box_aspect((ymax - ymin) / (xmax - xmin))
        self.ax.set_xlabel("x")
        self.ax.set_ylabel("y")
        self.ax.grid(False)
        self.ax.margins(0)

        self.position_artists: dict[str, PathCollection] = {}
        self.history_artists: dict[str, Line2D] = {}
        self.hue_history_artists: dict[str, LineCollection] = {}
        self.text_artists: dict[str, Text] = {}
        self.spline_artist: Line2D | None = None

        if self.state.app_config.palate_trace is not None:
            self.ax.plot(
                self.state.app_config.palate_trace[:, 0],
                self.state.app_config.palate_trace[:, 1],
                color=plt.rcParams["text.color"],
                linewidth=1.0,
            )
        if self.state.app_config.pharynx_trace is not None:
            self.ax.plot(
                self.state.app_config.pharynx_trace[:, 0],
                self.state.app_config.pharynx_trace[:, 1],
                color=plt.rcParams["text.color"],
                linewidth=1.0,
            )

        positions_by_name: dict[str, tuple[float, float]] = {}

        for traj in self.state.selected_value.trajectories.values():
            if (
                traj.kind != "spatial"
                or traj.name in self.state.app_config.spatial_exclude
            ):
                continue

            cursor_pos = round(self.state.cursor_s * traj.sample_rate_hz)
            head_pos = round(self.state.head_s * traj.sample_rate_hz)
            tail_pos = round(self.state.tail_s * traj.sample_rate_hz)

            x, y = traj.data[cursor_pos, 0], traj.data[cursor_pos, 1]
            positions_by_name[traj.name] = (x, y)
            self.position_artists[traj.name] = self.ax.scatter(
                [x], [y], s=35, color=self.state.colors[traj.name], zorder=10
            )
            xs = traj.data[head_pos:tail_pos, 0]
            ys = traj.data[head_pos:tail_pos, 1]

            self.history_artists[traj.name] = self.ax.plot(
                xs,
                ys,
                linewidth=0.8,
                color=self.state.colors[traj.name],
                visible=False,
            )[0]

            points = np.column_stack([xs, ys])
            segments = (
                np.stack([points[:-1], points[1:]], axis=1)
                if len(points) > 1
                else np.empty((0, 2, 2))
            )
            cmap = mpl.colormaps["hsv"]
            colors = cmap(np.linspace(0.0, 1.0, len(segments))) if len(segments) else []

            hue_artist = LineCollection(
                segments, colors=colors, linewidths=0.8, visible=False
            )
            self.ax.add_collection(hue_artist)
            self.hue_history_artists[traj.name] = hue_artist

            self.text_artists[traj.name] = self.ax.text(x, y, f" {traj.name}")

        if self.state.app_config.spline_trajs is not None:
            spline = compute_spline(
                self.state.app_config.spline_trajs,
                positions_by_name,
                self.state.app_config.polyline_spline,
            )
            if spline is not None:
                x_new, y_new = spline
                self.spline_artist = self.ax.plot(
                    x_new, y_new, linewidth=1.5, color=plt.rcParams["text.color"]
                )[0]

        self.canvas.draw_idle()

    def update_plot(
        self,
        cursor: bool = False,
        frame: bool = False,
        history_mode: bool | Literal["hue"] | None = None,
        colors: bool = False,
    ) -> None:
        if cursor:
            positions_by_name: dict[str, tuple[float, float]] = {}

            for traj in self.state.selected_value.trajectories.values():
                if (
                    traj.kind != "spatial"
                    or traj.name in self.state.app_config.spatial_exclude
                ):
                    continue

                cursor_pos = round(self.state.cursor_s * traj.sample_rate_hz)

                x, y = traj.data[cursor_pos, 0], traj.data[cursor_pos, 1]
                positions_by_name[traj.name] = (x, y)

                self.position_artists[traj.name].set_offsets([(x, y)])
                self.text_artists[traj.name].set_position((x, y))

            if self.spline_artist is not None:
                spline = compute_spline(
                    self.state.app_config.spline_trajs,
                    positions_by_name,
                    self.state.app_config.polyline_spline,
                )
                if spline is not None:
                    x_new, y_new = spline
                    self.spline_artist.set_data(x_new, y_new)

        # Avoid updating the history artists if it isn't visible, to save on performance.
        if frame and self.history is not False or history_mode:
            for traj in self.state.selected_value.trajectories.values():
                if (
                    traj.kind != "spatial"
                    or traj.name in self.state.app_config.spatial_exclude
                ):
                    continue

                head_pos = round(self.state.head_s * traj.sample_rate_hz)
                tail_pos = round(self.state.tail_s * traj.sample_rate_hz)

                xs = traj.data[head_pos:tail_pos, 0]
                ys = traj.data[head_pos:tail_pos, 1]

                self.history_artists[traj.name].set_data(xs, ys)

                points = np.column_stack([xs, ys])
                segments = (
                    np.stack([points[:-1], points[1:]], axis=1)
                    if len(points) > 1
                    else np.empty((0, 2, 2))
                )
                cmap = mpl.colormaps["hsv"]
                colors = (
                    cmap(np.linspace(0.0, 1.0, len(segments))) if len(segments) else []
                )

                hue_artist = self.hue_history_artists[traj.name]
                hue_artist.set_segments(segments)
                hue_artist.set_color(colors)

        if history_mode is not None:
            self.history = history_mode
            show_plain = history_mode is True
            show_hue = history_mode == "hue"

            for artist in self.history_artists.values():
                artist.set_visible(show_plain)

            for artist in self.hue_history_artists.values():
                artist.set_visible(show_hue)

        if colors:
            for k, artist in self.position_artists.items():
                artist.set_color(self.state.colors[k])
            for k, artist in self.history_artists.items():
                artist.set_color(self.state.colors[k])

        if cursor or frame or (history_mode is not None) or colors:
            self.canvas.draw_idle()
