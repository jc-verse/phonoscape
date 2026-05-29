from typing import cast

import numpy as np
import tkinter as tk
from tkinter import ttk

from mpl_toolkits.mplot3d.axes3d import Axes3D
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy.interpolate import splprep, splev

from ..state import PyViewState


def _set_spatial_axes(ax: Axes3D, xyz: np.ndarray, margin: float = 10) -> None:
    xyz = np.asarray(xyz, dtype=float)
    xyz = xyz[np.all(np.isfinite(xyz), axis=1)]

    if len(xyz) == 0:
        return

    mins = xyz.min(axis=0) - margin
    maxs = xyz.max(axis=0) + margin

    spans = maxs - mins

    # Avoid zero span in degenerate dimensions
    spans[spans == 0] = 1.0

    ax.set_xlim(mins[0], maxs[0])
    ax.set_ylim(mins[1], maxs[1])
    ax.set_zlim(mins[2], maxs[2])

    # Equal scale: physical box aspect proportional to data ranges.
    # This means one data unit has the same visual length in x/y/z.
    ax.set_box_aspect(spans)

    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_zlabel("")
    ax.grid(False)
    ax.margins(0)

    ax.view_init(elev=0, azim=-90)


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
            frameon=False,
        )
        self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0)

        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky="nsew")

    def plot(self) -> None:
        self.figure.clear()
        ax = cast(Axes3D, self.figure.add_axes((0.0, 0.0, 1.0, 1.0), projection="3d"))
        positions_by_name: dict[str, tuple[float, float, float]] = {}
        all_points: list[np.ndarray] = []

        for traj in self.state_model.selected_value.trajectories.values():
            if traj.kind != "spatial":
                continue

            pos = int(self.state_model.cursor_s * traj.sample_rate_hz)
            pos = max(0, min(traj.n_samples - 1, pos))

            x, y, z = traj.data[pos, 0], traj.data[pos, 1], traj.data[pos, 2]
            positions_by_name[traj.name] = (x, y, z)

            all_points.append(traj.data[:, :3])

            ax.scatter(
                [x], [y], [z], s=35, depthshade=False, color=traj.color, zorder=10
            )
            ax.text(x, y, z, f" {traj.name}", fontsize=7)

        if self.state_model.palate_variable is not None:
            palate_data = self.state_model.other_data[self.state_model.palate_variable]
            ax.plot(
                palate_data[:, 0],
                palate_data[:, 1],
                palate_data[:, 2],
                color=plt.rcParams["text.color"],
                linewidth=1.0,
            )
            all_points.append(palate_data[:, :3])

        if self.state_model.spline_trajs is not None:
            spline_points: list[tuple[float, float, float]] = []

            for name in self.state_model.spline_trajs:
                if name in positions_by_name:
                    spline_points.append(positions_by_name[name])
                elif name.upper() in positions_by_name:
                    spline_points.append(positions_by_name[name.upper()])
                else:
                    raise ValueError(
                        f"Spline trajectory '{name}' not found among spatial trajectories"
                    )

            if len(spline_points) < 2:
                return

            p = np.asarray(spline_points, dtype=float)
            k = min(3, len(spline_points) - 1)

            try:
                tck, _u = splprep([p[:, 0], p[:, 1], p[:, 2]], s=0, k=k)
                u_new = np.linspace(0, 1, 100)
                x_new, y_new, z_new = splev(u_new, tck)
                ax.plot(
                    x_new, y_new, z_new, linewidth=1.5, color=plt.rcParams["text.color"]
                )
            except Exception:
                ax.plot(
                    p[:, 0],
                    p[:, 1],
                    p[:, 2],
                    linewidth=1.0,
                    color=plt.rcParams["text.color"],
                )

        if all_points:
            points = np.vstack(all_points)
            _set_spatial_axes(ax, points)

        self.canvas.draw_idle()
