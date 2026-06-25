from typing import Literal, TypeAlias, cast, TYPE_CHECKING

import numpy as np

import matplotlib.pyplot as plt
import matplotlib.axes as plt_axes
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.colors import PowerNorm
from matplotlib.figure import Figure
from matplotlib.backend_bases import MouseEvent, LocationEvent
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D
from PySide6.QtWidgets import QWidget, QVBoxLayout

if TYPE_CHECKING:
    from .. import VarWindow

from ..state import (
    TrajDisplay,
    AudioTrajDisplay,
    ScalarTrajDisplay,
    SpatialTrajDisplay,
    get_component_names,
)
from ..data.process import get_plotting_data
from ..lproc.protocol import (
    LabelPlotContext,
    RenderedLabel,
    LabelUpdateResult,
    ClickContext,
)
from ..modals.label_modal import open_label_dialog
from ..modals.common_scaling_modal import get_visible_scaling

ArtistType: TypeAlias = (
    tuple[Literal["spatial-single"], Line2D]
    # Multiple components are recentered
    | tuple[Literal["spatial-multi"], list[Line2D]]
    | tuple[Literal["image"], AxesImage]
    | tuple[Literal["scalar"], Line2D]
)

DraggingState: TypeAlias = (
    Literal["cursor", "head", "tail", None]
    | tuple[Literal["frame"], float]
    | tuple[Literal["label"], int]
)


def contrast_gamma_from_db_range(data: np.ndarray, contrast: float):
    lo = np.nanpercentile(data, 1)
    hi = np.nanpercentile(data, 99.5)
    db_range = max(hi - lo, 1.0)

    target_db_below_peak = min(40.0, 0.5 * db_range)
    target_display_level = 0.12

    x = 1.0 - target_db_below_peak / db_range
    x = np.clip(x, 1e-6, 1.0 - 1e-6)

    gamma_max = np.log(target_display_level) / np.log(x)
    gamma_max = np.clip(gamma_max, 1.0, 30.0)

    return 1.0 + np.clip(contrast, 0.0, 1.0) * (gamma_max - 1.0)


class TemporalView(QWidget):
    def __init__(self, parent: QWidget, root: VarWindow):
        super().__init__(parent)

        self.root = root
        self.state = root.state
        self.dragging: DraggingState = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        width = parent.width() if parent.width() > 1 else 600
        height = parent.height() if parent.height() > 1 else 400
        dpi = self.screen().logicalDotsPerInch()

        self.figure = Figure(figsize=(width / dpi, height / dpi), dpi=dpi, frameon=True)

        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas)

        self.canvas.mpl_connect(
            "button_press_event", self._on_press  # pyright: ignore[reportArgumentType]
        )
        self.canvas.mpl_connect(
            "motion_notify_event",
            self._on_motion,  # pyright: ignore[reportArgumentType]
        )
        self.canvas.mpl_connect(
            "button_release_event",
            self._on_release,  # pyright: ignore[reportArgumentType]
        )
        self.canvas.mpl_connect(
            "figure_leave_event",
            self._on_figure_leave,  # pyright: ignore[reportArgumentType]
        )

        self.reset_plot()

    def reset_plot(self) -> None:
        self.figure.clear()
        self.figure.subplots_adjust(
            left=0.01, right=0.99, top=0.99, bottom=0.01, hspace=0
        )
        n = len(self.state.temporal_disp_specs)
        # Framing trajectory and spacing
        height_ratios = [1.0, 0.08] + [
            1.0 if spec.content != "SPECT" else 2.0
            for spec in self.state.temporal_disp_specs
        ]
        gs = self.figure.add_gridspec(
            nrows=len(height_ratios), ncols=1, height_ratios=height_ratios
        )
        self.axes = [self.figure.add_subplot(gs[0])] + [
            self.figure.add_subplot(gs[i + 2]) for i in range(n)
        ]

        self._refresh_plotting_data()
        # When the first trajectory of its kind is added, there is no computed
        # common scaling. We fill this in.
        # Otherwise, we should also invalidate previous computation/specification.
        if self.state.common_scaling is not None:
            self.state.common_scaling = get_visible_scaling(self)

        duration_s = self.state.selected_value.duration_s
        self.artists: list[ArtistType] = []
        self.zero_artists: list[Line2D | None] = []
        self.cursor_artists: list[Line2D] = []
        self.rendered_labels: list[list[RenderedLabel]] = []
        for i, ax, spec in zip(range(n + 1), self.axes, self._get_temp_disp_specs()):
            artist, zero_artist, cursor_artist, rendered_labels = self._plot_one_axis(
                ax, spec, i=i, duration_s=duration_s
            )
            self.artists.append(artist)
            self.zero_artists.append(zero_artist)
            self.cursor_artists.append(cursor_artist)
            self.rendered_labels.append(rendered_labels)

        if self.state.common_scaling:
            self.update_plot(spatial_ylim=True)
        else:
            self.canvas.draw_idle()

    def _plot_one_axis(
        self, ax: plt_axes.Axes, spec: TrajDisplay, i: int, duration_s: float
    ):
        traj = self.state.selected_value.trajectories[spec.traj_name]
        t, data = self.plotting_data[i]
        if isinstance(spec, SpatialTrajDisplay):
            # Plotting multiple components: recenter
            if len(spec.components) > 1:
                lines: list[Line2D] = []
                for j in range(data.shape[1]):
                    sub_data = data[:, j]
                    sub_data_center = (np.nanmax(sub_data) + np.nanmin(sub_data)) / 2
                    line = ax.plot(
                        t,
                        sub_data - sub_data_center,
                        linewidth=0.8,
                        label=spec.components[j],
                        color=self.state.colors[traj.name],
                        alpha=1 - j * 0.3,
                    )[0]
                    lines.append(line)
                ax.legend(
                    loc="upper right",
                    frameon=True,
                    borderpad=0.2,
                    handlelength=1.2,
                    handletextpad=0.3,
                )
                artist: ArtistType = ("spatial-multi", lines)
            else:
                artist = (
                    "spatial-single",
                    ax.plot(
                        t, data[:, 0], linewidth=0.8, color=self.state.colors[traj.name]
                    )[0],
                )
        elif spec.content == "SPECT":
            artist = (
                "image",
                ax.imshow(
                    data,
                    aspect="auto",
                    origin="lower",
                    extent=cast(tuple[float, float, float, float], t),
                    norm=PowerNorm(
                        gamma=contrast_gamma_from_db_range(data, spec.spect_contrast)
                    ),
                    cmap="gray_r",
                ),
            )
            ax.set_ylim(0, self.state.app_config.spectral_display_cutoff_hz)
        elif spec.content in ("SIGNAL", "RMS", "F0", "ZC", "MOVEMENT", "VEL", "ABSVEL"):
            artist = (
                "scalar",
                ax.plot(t, data, linewidth=0.8, color=self.state.colors[traj.name])[0],
            )
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

        if artist[0] in ("spatial-single", "scalar") and spec.content != "movement":
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
            if self.state.common_scaling is None:
                # Reset limits because invisible line still affects autoscaling
                ax.relim(visible_only=True)
                ax.autoscale(axis="y")
        else:
            zero_artist = None

        cursor_artist = ax.axvline(
            self.state.cursor_s,
            color=plt.rcParams["text.color"],
            linewidth=0.5,
            zorder=1000,
            clip_on=True,
        )

        if i == 0:
            ymin, ymax = ax.get_ylim()
            self.frame_artist = ax.fill_betweenx(
                [ymin, ymax],
                self.state.head_s,
                self.state.tail_s,
                color=plt.rcParams["text.color"],
                alpha=0.3,
                zorder=1000,
                clip_on=True,
            )

        rendered_labels: list[RenderedLabel] = []
        for label in self.state.labels:
            ctx = LabelPlotContext(ax=ax, ax_index=i, spec=spec)
            rendered_label = self.state.lproc.plot_label(label, ctx)
            rendered_labels.append(rendered_label)

        return artist, zero_artist, cursor_artist, rendered_labels

    def update_plot(
        self,
        cursor: bool = False,
        trajectories: bool = False,
        frame: bool = False,
        spect_ylim: bool = False,
        spatial_ylim: bool = False,
        labels: LabelUpdateResult | None = None,
    ) -> None:
        if not labels:
            labels = LabelUpdateResult()
        if cursor:
            for line in self.cursor_artists:
                line.set_xdata([self.state.cursor_s, self.state.cursor_s])
        specs = self._get_temp_disp_specs()
        if trajectories:
            self._refresh_plotting_data()
            for i, artist in enumerate(self.artists):
                t, data = self.plotting_data[i]
                if artist[0] == "image":
                    artist[1].set_data(data)
                    artist[1].set_extent(cast(tuple[float, float, float, float], t))
                elif artist[0] == "spatial-multi":
                    for j, line in enumerate(artist[1]):
                        sub_data = data[:, j]
                        sub_data_center = (
                            np.nanmax(sub_data) + np.nanmin(sub_data)
                        ) / 2
                        line.set_data(t, sub_data - sub_data_center)
                elif artist[0] == "spatial-single":
                    artist[1].set_data(t, data[:, 0])
                elif artist[0] == "scalar":
                    artist[1].set_data(t, data)
                ax = self.axes[i]
                if i == 0:
                    ax.set_xlim(0, self.state.selected_value.duration_s)
                if zero_artist := self.zero_artists[i]:
                    zero_artist.set_visible(False)
                if self.state.common_scaling is None or artist[0] in (
                    "image",
                    "scalar",
                ):
                    ax.relim(visible_only=True)
                    ax.autoscale(axis="y")
                # Otherwise the axis limits will be computed in spatial_ylim
                if zero_artist := self.zero_artists[i]:
                    ymin, ymax = ax.get_ylim()
                    zero_visible = ymin < 0 < ymax
                    zero_artist.set_visible(zero_visible)
        if spatial_ylim or trajectories:
            for spec, ax, artist, (_, data) in zip(
                specs, self.axes, self.artists, self.plotting_data
            ):
                if artist[0] not in ("spatial-single", "spatial-multi"):
                    continue
                if self.state.common_scaling is None:
                    ax.relim(visible_only=True)
                    ax.autoscale(axis="y")
                    continue
                scale = self.state.common_scaling[
                    (
                        0
                        if spec.content == "movement"
                        else 1 if spec.content == "velocity" else 2
                    )
                ]
                if artist[0] == "spatial-multi":
                    # Already centered
                    ax.set_ylim(-scale / 2, scale / 2)
                else:
                    data_center = (np.nanmax(data) + np.nanmin(data)) / 2
                    ax.set_ylim(data_center - scale / 2, data_center + scale / 2)

        framing_traj = self.state.selected_value.trajectories[
            self.state.app_config.framing_traj
        ]
        # All of these may update ylim
        if frame or ((spatial_ylim or trajectories) and framing_traj.kind == "spatial"):
            head_s = self.state.head_s
            tail_s = self.state.tail_s
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
        if spect_ylim:
            for i, spec in enumerate(specs):
                if spec.content == "SPECT":
                    ax = self.axes[i]
                    ax.set_ylim(0, self.state.app_config.spectral_display_cutoff_hz)
        for label_idx, label in labels.edited_labels.items():
            for i, ax_rendered_labels in enumerate(self.rendered_labels):
                # Always replot
                # TODO: perhaps the lproc can specify how to incrementally update
                for artist in ax_rendered_labels[label_idx].artists:
                    artist.remove()
                ctx = LabelPlotContext(ax=self.axes[i], ax_index=i, spec=specs[i])
                ax_rendered_labels[label_idx] = self.state.lproc.plot_label(label, ctx)
        for label_idx in labels.deleted_labels:
            for ax_rendered_labels in self.rendered_labels:
                for artist in ax_rendered_labels[label_idx].artists:
                    artist.remove()
        for label_idx in sorted(labels.deleted_labels, reverse=True):
            for ax_rendered_labels in self.rendered_labels:
                ax_rendered_labels.pop(label_idx)
        for label in labels.created_labels:
            for i, ax_rendered_labels in enumerate(self.rendered_labels):
                ctx = LabelPlotContext(ax=self.axes[i], ax_index=i, spec=specs[i])
                rendered_label = self.state.lproc.plot_label(label, ctx)
                ax_rendered_labels.append(rendered_label)

        if (
            cursor
            or trajectories
            or frame
            or spect_ylim
            or spatial_ylim
            or labels.created_labels
            or labels.edited_labels
            or labels.deleted_labels
        ):
            self.canvas.draw_idle()

    def _get_temp_disp_specs(self):
        framing_traj_name = self.state.app_config.framing_traj
        framing_traj = self.state.selected_value.trajectories[framing_traj_name]
        framing_traj_spec: TrajDisplay

        if framing_traj.kind == "scalar":
            framing_traj_spec = ScalarTrajDisplay(
                content="MOVEMENT", traj_name=framing_traj_name
            )
        elif framing_traj.kind == "audio":
            framing_traj_spec = AudioTrajDisplay(
                content="SIGNAL", traj_name=framing_traj_name
            )
        else:
            framing_traj_spec = SpatialTrajDisplay(
                content="movement",
                traj_name=framing_traj_name,
                traj_dims=self.state.app_config.dimensions,
                components=get_component_names(self.state.app_config.dimensions),
            )

        return [framing_traj_spec] + self.state.temporal_disp_specs

    def _refresh_plotting_data(self) -> None:
        self.plotting_data = [
            get_plotting_data(self.state.selected_value, spec, self.state.app_config)
            for spec in self._get_temp_disp_specs()
        ]

    def _event_is_in_cursor_axes(self, event) -> bool:
        return event.inaxes in self.axes and event.inaxes != self.axes[0]

    def _event_is_in_frame_axes(self, event) -> bool:
        return event.inaxes == self.axes[0]

    def _toolbar_is_active(self) -> bool:
        toolbar = getattr(self.canvas, "toolbar", None)
        return toolbar is not None and bool(getattr(toolbar, "mode", ""))

    def _on_press(self, event: MouseEvent) -> None:
        if (
            self._toolbar_is_active()
            or event.xdata is None
            or event.button != 1
            or not event.inaxes
        ):
            return
        if self._event_is_in_cursor_axes(event):
            idx = self.axes.index(event.inaxes)
            spec = self._get_temp_disp_specs()[idx]
            self.root.readout.readout_traj(
                spec, self.plotting_data[idx][1], event.xdata
            )
            closest_label = None
            closest_dist = float("inf")
            for i, label in enumerate(self.state.labels):
                dist = abs(event.xdata - label.offset_s)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_label = i
            if (
                closest_label is not None
                and any(
                    a.contains(event)[0]
                    for a in self.rendered_labels[idx][closest_label].hit_test_artists
                )
                > 0
            ):
                if event.dblclick:
                    open_label_dialog(self, ("edit", closest_label))
                else:
                    self.dragging = ("label", closest_label)
                return
            self.dragging = "cursor"
            self.root.set_cursor(event.xdata, keep_readout=True)
        elif self._event_is_in_frame_axes(event):
            if event.dblclick:
                self.root.set_selection(0, self.state.selected_value.duration_s)
                return
            dist_to_head = abs(event.xdata - self.state.head_s)
            dist_to_tail = abs(event.xdata - self.state.tail_s)
            # Consistent with MVIEW's hitbox
            # Can't use matplotlib's hit-testing because this is not a line
            thres_dist = 0.008 * self.state.selected_value.duration_s
            if dist_to_head < dist_to_tail and dist_to_head < thres_dist:
                self.dragging = "head"
                self.root.set_head(event.xdata)
            elif dist_to_tail < dist_to_head and dist_to_tail < thres_dist:
                self.dragging = "tail"
                self.root.set_tail(event.xdata)
            elif self.state.head_s < event.xdata < self.state.tail_s:
                self.dragging = ("frame", event.xdata)

    def _on_motion(self, event: MouseEvent) -> None:
        if not self.dragging or event.xdata is None or event.inaxes is None:
            return
        if self._event_is_in_cursor_axes(event):
            idx = self.axes.index(event.inaxes)
            spec = self._get_temp_disp_specs()[idx]
            self.root.readout.readout_traj(
                spec, self.plotting_data[idx][1], event.xdata
            )
        if self.dragging == "cursor":
            if self._event_is_in_cursor_axes(event):
                self.root.set_cursor(event.xdata, keep_readout=True)
            else:
                # Cancel drag if moved outside of axes
                self.dragging = None
        elif self.dragging == "head":
            if self._event_is_in_frame_axes(event):
                self.root.set_head(event.xdata)
            else:
                self.dragging = None
        elif self.dragging == "tail":
            if self._event_is_in_frame_axes(event):
                self.root.set_tail(event.xdata)
            else:
                self.dragging = None
        elif isinstance(self.dragging, tuple) and self.dragging[0] == "frame":
            old_loc = self.dragging[1]
            if self._event_is_in_frame_axes(event):
                self.root.move_selection(event.xdata - old_loc)
                self.dragging = ("frame", event.xdata)
            else:
                self.dragging = None
        elif isinstance(self.dragging, tuple) and self.dragging[0] == "label":
            label_idx = self.dragging[1]
            if self._event_is_in_cursor_axes(event):
                self.dragging = ("label", label_idx)
                result = self.state.lproc.edit_label(label_idx, offset_s=event.xdata)
                self.state.apply_label_update(result)
                self.update_plot(labels=result)
            else:
                self.dragging = None

    def _on_release(self, event: MouseEvent) -> None:
        self.dragging = None
        if (
            event.button == 3
            and self._event_is_in_cursor_axes(event)
            and event.inaxes is not None
            and event.xdata is not None
        ):
            # TODO: modified click / shift-click
            idx = self.axes.index(event.inaxes)
            open_label_dialog(
                self,
                ("create", event.xdata),
                click_context=ClickContext(
                    ax=event.inaxes,
                    ax_index=idx,
                    spec=self._get_temp_disp_specs()[idx],
                    modifiers=set(),
                    button=3,
                ),
            )

    def _on_figure_leave(self, event: LocationEvent) -> None:
        self.dragging = None
