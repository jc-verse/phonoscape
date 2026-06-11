from typing import cast, Any

import numpy as np
from scipy.interpolate import splprep, splev

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.collections import PathCollection
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.text import Text
from PySide6.QtWidgets import QWidget, QVBoxLayout

from ..state import WindowState


class SpatialView2D(QWidget):
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
            if traj.kind != "spatial" or traj.name in self.state.app_config.spatial_exclude:
                continue

            pos = round(self.state.cursor_s * traj.sample_rate_hz)
            pos = max(0, min(traj.n_samples - 1, pos))

            x, y = traj.data[pos, 0], traj.data[pos, 1]
            positions_by_name[traj.name] = (x, y)
            self.position_artists[traj.name] = self.ax.scatter(
                [x], [y], s=35, color=traj.color, zorder=10
            )
            self.text_artists[traj.name] = self.ax.text(x, y, f" {traj.name}")

        if self.state.app_config.spline_trajs is not None:
            spline = self._compute_spline(positions_by_name)
            if spline is not None:
                x_new, y_new = spline
                self.spline_artist = self.ax.plot(
                    x_new, y_new, linewidth=1.5, color=plt.rcParams["text.color"]
                )[0]

        self.canvas.draw_idle()

    def update_plot(self, points: bool = False) -> None:
        if points:
            positions_by_name: dict[str, tuple[float, float]] = {}

            for traj in self.state.selected_value.trajectories.values():
                if traj.kind != "spatial" or traj.name in self.state.app_config.spatial_exclude:
                    continue

                pos = round(self.state.cursor_s * traj.sample_rate_hz)
                pos = max(0, min(traj.n_samples - 1, pos))

                x, y = traj.data[pos, 0], traj.data[pos, 1]
                positions_by_name[traj.name] = (x, y)

                self.position_artists[traj.name].set_offsets([(x, y)])
                self.text_artists[traj.name].set_position((x, y))

            if self.spline_artist is not None:
                spline = self._compute_spline(positions_by_name)
                if spline is not None:
                    x_new, y_new = spline
                    self.spline_artist.set_data(x_new, y_new)

        if points:
            self.canvas.draw_idle()

    def _compute_spline(
        self, positions_by_name: dict[str, tuple[float, float]]
    ) -> tuple[Any, Any] | None:
        assert self.state.app_config.spline_trajs is not None

        spline_points: list[tuple[float, float]] = []

        for name in self.state.app_config.spline_trajs:
            if name in positions_by_name:
                spline_points.append(positions_by_name[name])
            else:
                raise ValueError(
                    f"Spline trajectory '{name}' not found among spatial trajectories"
                )

        if len(spline_points) < 2:
            return None

        p = np.asarray(spline_points, dtype=float)
        k = min(3, len(spline_points) - 1)
        x_raw, y_raw = p[:, 0], p[:, 1]

        try:
            tck, _u = splprep([x_raw, y_raw], s=0, k=k)
            u_new = np.linspace(0, 1, 100)
            x_new, y_new = splev(u_new, tck)
            return x_new, y_new
        except Exception:
            return x_raw, y_raw
