from typing import cast, Any

import numpy as np
import tkinter as tk
from tkinter import ttk

from mpl_toolkits.mplot3d.axes3d import Axes3D
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.mplot3d.art3d import Path3DCollection, Line3D, Text3D
from scipy.interpolate import splprep, splev

from ..state import PyViewState


class SpatialView(ttk.Frame):
    def __init__(self, parent: tk.Widget, state_model: PyViewState):
        super().__init__(parent)

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
            frameon=True,
        )
        self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0)

        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky="nsew")

        self.figure.clear()
        self.ax: Axes3D = self.figure.add_subplot(111, projection="3d")
        
        xmin, xmax, ymin, ymax, zmin, zmax = self.state_model.spatial_bounds
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
        self.text_artists: dict[str, Text3D] = {}
        self.spline_artist: Line3D | None = None

        if self.state_model.config.palate_trace is not None:
            self.ax.plot(
                self.state_model.config.palate_trace[:, 0],
                self.state_model.config.palate_trace[:, 1],
                self.state_model.config.palate_trace[:, 2],
                color=plt.rcParams["text.color"],
                linewidth=1.0,
            )

        positions_by_name: dict[str, tuple[float, float, float]] = {}

        for traj in self.state_model.selected_value.trajectories.values():
            if traj.kind != "spatial":
                continue

            pos = int(self.state_model.cursor_s * traj.sample_rate_hz)
            pos = max(0, min(traj.n_samples - 1, pos))

            x, y, z = traj.data[pos, 0], traj.data[pos, 1], traj.data[pos, 2]
            positions_by_name[traj.name] = (x, y, z)
            self.position_artists[traj.name] = cast(
                Path3DCollection,
                self.ax.scatter(
                    [x], [y], [z], s=35, depthshade=False, color=traj.color, zorder=10
                ),
            )
            self.text_artists[traj.name] = cast(
                Text3D, self.ax.text(x, y, z, f" {traj.name}")
            )

        if self.state_model.config.spline_trajs is not None:
            spline = self._compute_spline(positions_by_name)
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

    def update_plot(self, points: bool = False) -> None:
        if points:
            positions_by_name: dict[str, tuple[float, float, float]] = {}

            for traj in self.state_model.selected_value.trajectories.values():
                if traj.kind != "spatial":
                    continue

                pos = int(self.state_model.cursor_s * traj.sample_rate_hz)
                pos = max(0, min(traj.n_samples - 1, pos))

                x, y, z = traj.data[pos, 0], traj.data[pos, 1], traj.data[pos, 2]
                positions_by_name[traj.name] = (x, y, z)
                self.position_artists[traj.name]._offsets3d = ([x], [y], [z])
                self.text_artists[traj.name].set_position((x, y))
                self.text_artists[traj.name].set_3d_properties(z, zdir="x")

            if self.spline_artist is not None:
                spline = self._compute_spline(positions_by_name)
                if spline is not None:
                    x_new, y_new, z_new = spline
                    self.spline_artist.set_data(x_new, y_new)
                    self.spline_artist.set_3d_properties(z_new)

        if points:
            self.canvas.draw_idle()

    def _compute_spline(
        self, positions_by_name: dict[str, tuple[float, float, float]]
    ) -> tuple[Any, Any, Any] | None:
        assert self.state_model.config.spline_trajs is not None

        spline_points: list[tuple[float, float, float]] = []

        for name in self.state_model.config.spline_trajs:
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
        x_raw, y_raw, z_raw = p[:, 0], p[:, 1], p[:, 2]

        try:
            tck, _u = splprep([x_raw, y_raw, z_raw], s=0, k=k)
            u_new = np.linspace(0, 1, 100)
            x_new, y_new, z_new = splev(u_new, tck)
            return x_new, y_new, z_new
        except Exception:
            return x_raw, y_raw, z_raw
