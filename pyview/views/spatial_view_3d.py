from typing import cast, Literal

import numpy as np

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.axes3d import Axes3D
from mpl_toolkits.mplot3d.art3d import (
    Path3DCollection,
    Line3D,
    Text3D,
    Line3DCollection,
)
from PySide6.QtWidgets import QWidget, QVBoxLayout

from ..state import WindowState
from ..data.process import compute_spline


class SpatialView3D(QWidget):
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
        self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0)

        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas)

        self.figure.clear()
        self.ax: Axes3D = self.figure.add_subplot(111, projection="3d")

        xmin, xmax, ymin, ymax, zmin, zmax = cast(
            tuple[float, float, float, float, float, float],
            self.state.app_config.spatial_bounds,
        )
        xmin -= (xmax - xmin) * 0.05
        xmax += (xmax - xmin) * 0.05
        ymin -= (ymax - ymin) * 0.05
        ymax += (ymax - ymin) * 0.05
        zmin -= (zmax - zmin) * 0.05
        zmax += (zmax - zmin) * 0.05
        self.ax.xaxis.pane.fill = False
        self.ax.yaxis.pane.fill = False
        self.ax.zaxis.pane.fill = False
        self.ax.set_xlim(xmin, xmax)
        self.ax.set_ylim(ymin, ymax)
        self.ax.set_zlim(zmin, zmax)
        # Equal scale: physical box aspect proportional to data ranges.
        # This means one data unit has the same visual length in x/y/z.
        self.ax.set_box_aspect((xmax - xmin, ymax - ymin, zmax - zmin))
        self.ax.set_xlabel("x")
        self.ax.set_ylabel("y")
        self.ax.set_zlabel("z")
        self.ax.grid(False)
        self.ax.margins(0)

        self.position_artists: dict[str, Path3DCollection] = {}
        self.history_artists: dict[str, Line3D] = {}
        self.hue_history_artists: dict[str, Line3DCollection] = {}
        self.text_artists: dict[str, Text3D] = {}
        self.spline_artist: Line3D | None = None

        if self.state.app_config.palate_trace is not None:
            self.ax.plot(
                self.state.app_config.palate_trace[:, 0],
                self.state.app_config.palate_trace[:, 1],
                self.state.app_config.palate_trace[:, 2],
                color=plt.rcParams["text.color"],
                linewidth=1.0,
            )
        if self.state.app_config.pharynx_trace is not None:
            self.ax.plot(
                self.state.app_config.pharynx_trace[:, 0],
                self.state.app_config.pharynx_trace[:, 1],
                self.state.app_config.pharynx_trace[:, 2],
                color=plt.rcParams["text.color"],
                linewidth=1.0,
            )

        positions_by_name: dict[str, tuple[float, float, float]] = {}

        for traj in self.state.selected_value.trajectories.values():
            if (
                traj.kind != "spatial"
                or traj.name in self.state.app_config.spatial_exclude
            ):
                continue

            cursor_pos = round(self.state.cursor_s * traj.sample_rate_hz)
            head_pos = round(self.state.head_s * traj.sample_rate_hz)
            tail_pos = round(self.state.tail_s * traj.sample_rate_hz)

            x, y, z = (
                traj.data[cursor_pos, 0],
                traj.data[cursor_pos, 1],
                traj.data[cursor_pos, 2],
            )
            positions_by_name[traj.name] = (x, y, z)
            self.position_artists[traj.name] = cast(
                Path3DCollection,
                self.ax.scatter(
                    [x],
                    [y],
                    [z],
                    s=35,
                    depthshade=False,
                    color=self.state.colors[traj.name],
                    zorder=10,
                ),
            )
            xs = traj.data[head_pos:tail_pos, 0]
            ys = traj.data[head_pos:tail_pos, 1]
            zs = traj.data[head_pos:tail_pos, 2]

            self.history_artists[traj.name] = cast(
                Line3D,
                self.ax.plot(
                    xs,
                    ys,
                    zs,
                    linewidth=0.8,
                    color=self.state.colors[traj.name],
                    visible=False,
                )[0],
            )

            points = np.column_stack([xs, ys, zs])
            segments = (
                np.stack([points[:-1], points[1:]], axis=1)
                if len(points) > 1
                else np.empty((0, 2, 3))
            )
            cmap = mpl.colormaps["hsv"]
            colors = (
                cmap(np.linspace(0.0, 1.0, len(segments)))
                if len(segments)
                else np.empty((0, 4))
            )

            hue_artist = Line3DCollection(
                segments, colors=colors, linewidths=0.8, visible=False
            )
            self.ax.add_collection3d(hue_artist)
            self.hue_history_artists[traj.name] = hue_artist

            self.text_artists[traj.name] = cast(
                Text3D, self.ax.text(x, y, z, f" {traj.name}")
            )

        if self.state.app_config.spline_trajs is not None:
            spline = compute_spline(
                self.state.app_config.spline_trajs,
                positions_by_name,
                self.state.app_config.polyline_spline,
            )
            if spline is not None:
                x_new, y_new, z_new = spline
                self.spline_artist = cast(
                    Line3D,
                    self.ax.plot(
                        x_new,
                        y_new,
                        z_new,
                        linewidth=1.5,
                        color=plt.rcParams["text.color"],
                    )[0],
                )

        self.canvas.draw_idle()

    def update_plot(
        self,
        cursor: bool = False,
        frame: bool = False,
        history_mode: bool | Literal["hue"] | None = None,
        colors: bool = False,
    ) -> None:
        if cursor:
            positions_by_name: dict[str, tuple[float, float, float]] = {}

            for traj in self.state.selected_value.trajectories.values():
                if (
                    traj.kind != "spatial"
                    or traj.name in self.state.app_config.spatial_exclude
                ):
                    continue

                cursor_pos = round(self.state.cursor_s * traj.sample_rate_hz)

                x, y, z = (
                    traj.data[cursor_pos, 0],
                    traj.data[cursor_pos, 1],
                    traj.data[cursor_pos, 2],
                )
                positions_by_name[traj.name] = (x, y, z)
                self.position_artists[traj.name]._offsets3d = ([x], [y], [z])
                self.text_artists[traj.name].set_position((x, y))
                self.text_artists[traj.name].set_3d_properties(z, zdir="x")

            if self.spline_artist is not None:
                spline = compute_spline(
                    self.state.app_config.spline_trajs,
                    positions_by_name,
                    self.state.app_config.polyline_spline,
                )
                if spline is not None:
                    x_new, y_new, z_new = spline
                    self.spline_artist.set_data(x_new, y_new)
                    self.spline_artist.set_3d_properties(z_new)

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
                zs = traj.data[head_pos:tail_pos, 2]

                self.history_artists[traj.name].set_data_3d(xs, ys, zs)

                points = np.column_stack([xs, ys, zs])
                segments = (
                    np.stack([points[:-1], points[1:]], axis=1)
                    if len(points) > 1
                    else np.empty((0, 2, 3))
                )
                cmap = mpl.colormaps["hsv"]
                colors = (
                    cmap(np.linspace(0.0, 1.0, len(segments)))
                    if len(segments)
                    else np.empty((0, 4))
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
