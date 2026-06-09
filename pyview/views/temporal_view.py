from typing import Literal, TYPE_CHECKING

import matplotlib.pyplot as plt
import matplotlib.axes as plt_axes
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D
from matplotlib.text import Text
from PySide6.QtWidgets import QWidget, QVBoxLayout

if TYPE_CHECKING:
    from .. import PyViewWindow

from ..state import TrajDisplay, ScalarTrajDisplay, SpatialTrajDisplay, Label
from ..data.process import get_plotting_data
from ..modals.label_modal import open_label_dialog

ArtistType = (
    tuple[Literal["spatial"], list[Line2D]]
    | tuple[Literal["image"], AxesImage]
    | tuple[Literal["scalar"], Line2D]
)


class TemporalView(QWidget):
    def __init__(
        self,
        parent: QWidget,
        root: PyViewWindow,
    ):
        super().__init__(parent)

        self.root = root
        self.dragging: (
            Literal["cursor", "head", "tail", None]
            | tuple[Literal["frame"], float]
            | tuple[Literal["label"], int]
        ) = None
        self.state_model = root.state_model

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        width = parent.width() if parent.width() > 1 else 600
        height = parent.height() if parent.height() > 1 else 400
        dpi = self.screen().logicalDotsPerInch()

        self.figure = Figure(figsize=(width / dpi, height / dpi), dpi=dpi, frameon=True)

        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas)

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
        self.label_artists: list[dict[Label, Line2D]] = []
        self.label_text_artists: list[dict[Label, Text]] = []
        for i, ax, spec in zip(range(n + 1), self.axes, self._get_temp_disp_specs()):
            artist, zero_artist, cursor_artist, label_artists, label_text_artists = (
                self._plot_one_axis(ax, spec, i=i, duration_s=duration_s)
            )
            self.artists.append(artist)
            self.zero_artists.append(zero_artist)
            self.cursor_artists.append(cursor_artist)
            self.label_artists.append(label_artists)
            if label_text_artists is not None:
                self.label_text_artists.append(label_text_artists)

        self.canvas.draw_idle()

    def update_plot(
        self,
        cursor: bool = False,
        trajectories: bool = False,
        frame: bool = False,
        labels: list[Label] | None = None,
    ) -> None:
        if cursor:
            for line in self.cursor_artists:
                line.set_xdata([self.state_model.cursor_s, self.state_model.cursor_s])
        if trajectories:
            self._refresh_plotting_data()
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
        if labels:
            for label in labels:
                if label not in self.state_model.labels:
                    # Label deleted
                    for label_artists in self.label_artists:
                        if label in label_artists:
                            label_artists[label].remove()
                            del label_artists[label]
                    for label_text_artists in self.label_text_artists:
                        if label in label_text_artists:
                            label_text_artists[label].remove()
                            del label_text_artists[label]
                else:
                    # Label added or updated
                    for i, label_artists in enumerate(self.label_artists):
                        if label in label_artists:
                            la = label_artists[label]
                            la.set_xdata([label.offset_s, label.offset_s])
                        else:
                            ax = self.axes[i]
                            label_artists[label] = ax.axvline(
                                label.offset_s,
                                color="red",
                                linewidth=0.8,
                                zorder=999,
                                clip_on=True,
                            )
                    for i, label_text_artists in enumerate(self.label_text_artists):
                        if label in label_text_artists:
                            lta = label_text_artists[label]
                            lta.set_x(label.offset_s)
                        else:
                            ax = self.axes[i]
                            text = ax.text(
                                label.offset_s,
                                0.5,
                                label.name,
                                color="red",
                                zorder=999,
                                clip_on=True,
                            )
                            label_text_artists[label] = text
        if cursor or trajectories or frame or labels:
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
            "F0",
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

        label_artists: dict[Label, Line2D] = {}
        for label in self.state_model.labels:
            label_artists[label] = ax.axvline(
                label.offset_s, color="red", linewidth=0.8, zorder=999, clip_on=True
            )

        if i == 0 or i == 1:
            label_text_artists: dict[Label, Text] | None = {}
            # Only plot label for framing and first real data trajectory
            for label in self.state_model.labels:
                text = ax.text(
                    label.offset_s,
                    0.98,
                    label.name,
                    ha="left",
                    va="top",
                    color="red",
                    zorder=999,
                    clip_on=False,
                )
                label_text_artists[label] = text
        else:
            label_text_artists = None

        return artist, zero_artist, cursor_artist, label_artists, label_text_artists

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
                components=["x", "y", "z"][: self.state_model.dimensions],
            )
        )
        return [framing_traj_spec] + self.state_model.config.temporal_disp_specs

    def _refresh_plotting_data(self) -> None:
        self.plotting_data = [
            get_plotting_data(
                self.state_model.selected_value, spec, self.state_model.dimensions
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
        if self._toolbar_is_active() or event.xdata is None or event.button != 1:
            return
        if self._event_is_in_cursor_axes(event):
            for i, label in enumerate(self.state_model.labels):
                closest_label = None
                closest_dist = float("inf")
                for i, label in enumerate(self.state_model.labels):
                    dist = abs(event.xdata - label.offset_s)
                    if dist < closest_dist:
                        closest_dist = dist
                        closest_label = i
                # Smaller hitbox for labels
                if closest_label is not None and closest_dist < 0.01 * (
                    self.state_model.tail_s - self.state_model.head_s
                ):
                    if event.dblclick:
                        open_label_dialog(self, ("edit", closest_label))
                    else:
                        self.dragging = ("label", closest_label)
                    return
            self.dragging = "cursor"
            self.root.set_cursor(float(event.xdata))
        elif self._event_is_in_frame_axes(event):
            if event.dblclick:
                self.root.set_selection(0, self.state_model.selected_value.duration_s)
                return
            loc = float(event.xdata)
            dist_to_head = abs(loc - self.state_model.head_s)
            dist_to_tail = abs(loc - self.state_model.tail_s)
            # Allow a 5% hitbox around each edge
            thres_dist = 0.025 * self.state_model.selected_value.duration_s
            if dist_to_head < dist_to_tail and dist_to_head < thres_dist:
                self.dragging = "head"
                self.root.set_head(loc)
            elif dist_to_tail < dist_to_head and dist_to_tail < thres_dist:
                self.dragging = "tail"
                self.root.set_tail(loc)
            elif self.state_model.head_s < loc < self.state_model.tail_s:
                self.dragging = ("frame", loc)

    def _on_motion(self, event) -> None:
        if not self.dragging or event.xdata is None:
            return
        if self.dragging == "cursor":
            if self._event_is_in_cursor_axes(event):
                self.root.set_cursor(float(event.xdata))
            else:
                # Cancel drag if moved outside of axes
                self.dragging = None
        elif self.dragging == "head":
            if self._event_is_in_frame_axes(event):
                self.root.set_head(float(event.xdata))
            else:
                self.dragging = None
        elif self.dragging == "tail":
            if self._event_is_in_frame_axes(event):
                self.root.set_tail(float(event.xdata))
            else:
                self.dragging = None
        elif isinstance(self.dragging, tuple) and self.dragging[0] == "frame":
            old_loc = self.dragging[1]
            if self._event_is_in_frame_axes(event):
                loc = float(event.xdata)
                self.root.move_selection(loc - old_loc)
                self.dragging = ("frame", loc)
            else:
                self.dragging = None
        elif isinstance(self.dragging, tuple) and self.dragging[0] == "label":
            label_idx = self.dragging[1]
            if self._event_is_in_cursor_axes(event):
                new_label, old_label = self.state_model.edit_label(
                    label_idx, offset_s=float(event.xdata)
                )
                self.dragging = ("label", label_idx)
                self.update_plot(labels=[new_label, old_label])
            else:
                self.dragging = None

    def _on_release(self, event) -> None:
        self.dragging = None
        if (
            event.button == 3
            and self._event_is_in_cursor_axes(event)
            and event.xdata is not None
        ):
            open_label_dialog(self, ("create", float(event.xdata)))

    def _on_figure_leave(self, event) -> None:
        self.dragging = None
