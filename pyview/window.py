from pathlib import Path
from typing import cast, Literal, Unpack

import matplotlib.pyplot as plt
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QMainWindow,
    QWidget,
    QLineEdit,
    QGridLayout,
    QVBoxLayout,
    QHBoxLayout,
)

from .data.parse import load_variables, normalize_args, PyViewArgs
from .data.process import get_plotting_data
from .menu.menu_bar import MenuBar
from .state import PyViewState, ScalarTrajDisplay
from .widgets.play_button import PlayButton, modes as play_modes
from .views.temporal_view import TemporalView
from .views.spatial_view_3d import SpatialView3D
from .views.spatial_view_2d import SpatialView2D
from .views.freq_domain_view import FreqDomainView


class PyViewWindow(QMainWindow):
    def __init__(
        self,
        file: str | Path,
        variables: str = "*",
        **kwargs: Unpack[PyViewArgs],
    ):
        super().__init__()
        plt.style.use("dark_background")

        path = Path(file)
        data, other_data, dimensions = load_variables(
            path, variables, comps=kwargs.get("comps")
        )

        if not data:
            raise ValueError(f"No matching variables found for pattern {variables!r}")

        config = normalize_args(kwargs, data, other_data, dimensions)

        min_x, min_y, min_z = float("inf"), float("inf"), float("inf")
        max_x, max_y, max_z = float("-inf"), float("-inf"), float("-inf")
        for variable in data.values():
            for traj in variable.trajectories.values():
                if traj.kind != "spatial":
                    continue
                if dimensions == 3:
                    x, y, z = traj.data.T
                    min_x, max_x = min(min_x, x.min()), max(max_x, x.max())
                    min_y, max_y = min(min_y, y.min()), max(max_y, y.max())
                    min_z, max_z = min(min_z, z.min()), max(max_z, z.max())
                else:
                    x, y = traj.data.T
                    min_x, max_x = min(min_x, x.min()), max(max_x, x.max())
                    min_y, max_y = min(min_y, y.min()), max(max_y, y.max())
        if config.palate_trace is not None:
            palate_trace = config.palate_trace
            if dimensions == 3:
                x, y, z = palate_trace.T
                min_x, max_x = min(min_x, x.min()), max(max_x, x.max())
                min_y, max_y = min(min_y, y.min()), max(max_y, y.max())
                min_z, max_z = min(min_z, z.min()), max(max_z, z.max())
            else:
                x, y = palate_trace.T
                min_x, max_x = min(min_x, x.min()), max(max_x, x.max())
                min_y, max_y = min(min_y, y.min()), max(max_y, y.max())

        selected_variable = next(iter(data.keys()))

        head_s = (kwargs.get("head") or 0) / 1000
        tail_s = (
            kwargs.get("tail") or data[selected_variable].duration_s * 1000
        ) / 1000
        tail_s = min(tail_s, data[selected_variable].duration_s)
        if head_s < 0:
            raise ValueError(
                f"--head must be a non-negative number of milliseconds, but got {head_s * 1000}"
            )
        if tail_s < 0:
            raise ValueError(
                f"--tail must be a non-negative number of milliseconds, but got {tail_s * 1000}"
            )
        if head_s >= tail_s:
            raise ValueError(
                f"--head must be less than --tail, but got head={head_s * 1000} and tail={tail_s * 1000}"
            )
        elif tail_s - head_s < 0.025:
            raise ValueError(
                f"The duration of the selection (tail - head) must be at least 25 milliseconds, but got head={head_s * 1000} and tail={tail_s * 1000} ({(tail_s - head_s) * 1000:.1f} ms)"
            )

        self.state_model = PyViewState(
            file=path,
            data=data,
            other_data=other_data,
            custom={},
            labels=[],
            audio_spect=(
                get_plotting_data(
                    data[selected_variable].trajectories[config.audio_traj],
                    ScalarTrajDisplay(traj_name=config.audio_traj, content="SPECT"),
                    dimensions,
                )
                if config.audio_traj is not None
                else None
            ),
            selected_variable=selected_variable,
            dimensions=cast(Literal[2, 3], dimensions),
            spatial_bounds=(
                (min_x, max_x, min_y, max_y, min_z, max_z)
                if dimensions == 3
                else (min_x, max_x, min_y, max_y)
            ),
            config=config,
            cursor_s=0.0,
            head_s=head_s,
            tail_s=tail_s,
            play_mode=play_modes[0],
        )

        self.setWindowTitle(f"PyView - {path.name}")
        self.resize(1440, 1000)

        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        root_layout = QGridLayout(central)
        root_layout.setContentsMargins(4, 0, 4, 4)
        root_layout.setHorizontalSpacing(4)
        root_layout.setVerticalSpacing(4)

        root_layout.setRowStretch(0, 0)
        root_layout.setRowStretch(1, 1)
        root_layout.setColumnStretch(0, 1)
        root_layout.setColumnStretch(1, 2)

        navbar = QFrame(central)
        navbar_layout = QHBoxLayout(navbar)
        navbar_layout.setContentsMargins(8, 6, 8, 6)
        navbar_layout.setSpacing(12)

        root_layout.addWidget(navbar, 0, 0, 1, 2)

        self.info_label = QLabel(
            f"{self.state_model.selected_variable} "
            f"({self.state_model.data[self.state_model.selected_variable].duration_s:.2f}s)",
            navbar,
        )
        navbar_layout.addWidget(self.info_label)

        if self.state_model.config.audio_traj is not None:
            play_button = PlayButton(navbar, self.state_model)
            play_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            navbar_layout.addWidget(play_button)

        def add_navbar_time_box(label_text: str, value: float, callback) -> QLineEdit:
            group = QWidget(navbar)
            group_layout = QHBoxLayout(group)
            group_layout.setContentsMargins(0, 0, 0, 0)
            group_layout.setSpacing(4)

            label = QLabel(f"{label_text}", group)

            box = QLineEdit(group)
            box.setText(f"{value:.1f}")
            box.setFixedWidth(70)
            box.setAlignment(Qt.AlignmentFlag.AlignRight)
            box.returnPressed.connect(callback)

            label.setBuddy(box)

            group_layout.addWidget(label)
            group_layout.addWidget(box)

            navbar_layout.addWidget(group)

            return box

        self.cursor_box = add_navbar_time_box(
            "Cursor", self.state_model.cursor_s * 1000, self.set_cursor
        )
        self.head_box = add_navbar_time_box(
            "Head", self.state_model.head_s * 1000, self.set_head
        )
        self.tail_box = add_navbar_time_box(
            "Tail", self.state_model.tail_s * 1000, self.set_tail
        )

        navbar_layout.addStretch(1)

        left = QFrame(central)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        root_layout.addWidget(left, 1, 0)

        if self.state_model.dimensions == 3:
            self.spatial_view = SpatialView3D(left, state_model=self.state_model)
        else:
            self.spatial_view = SpatialView2D(left, state_model=self.state_model)
        left_layout.addWidget(self.spatial_view, stretch=1)

        self.freq_domain_view = FreqDomainView(left, state_model=self.state_model)
        left_layout.addWidget(self.freq_domain_view, stretch=1)

        right = QFrame(central)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        root_layout.addWidget(right, 1, 1)

        self.temporal_view = TemporalView(right, self)
        right_layout.addWidget(self.temporal_view, stretch=1)

        # Important: create menu bar after views, because it directly manipulates them.
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)

        self.setFocus()

    def set_cursor(self, cursor_s: float) -> None:
        cursor_s = min(max(0, cursor_s), self.state_model.selected_value.duration_s)
        self.state_model.cursor_s = cursor_s
        self.cursor_box.setText(f"{cursor_s * 1000:.1f}")
        self.temporal_view.update_plot(cursor=True)
        self.spatial_view.update_plot(points=True)
        if self.state_model.config.audio_traj is not None:
            self.freq_domain_view.update_plot()

    def set_head(self, head_s: float) -> None:
        head_s = min(self.state_model.tail_s - self.state_model.min_sel_dur_s, head_s)
        self.state_model.head_s = head_s
        self.head_box.setText(f"{head_s * 1000:.1f}")
        self.temporal_view.update_plot(frame=True)

    def set_tail(self, tail_s: float) -> None:
        tail_s = max(self.state_model.head_s + self.state_model.min_sel_dur_s, tail_s)
        self.state_model.tail_s = tail_s
        self.tail_box.setText(f"{tail_s * 1000:.1f}")
        self.temporal_view.update_plot(frame=True)
    
    def set_selection(self, head_s: float, tail_s: float) -> None:
        width = tail_s - head_s
        if width < self.state_model.min_sel_dur_s:
            mid = (head_s + tail_s) / 2
            head_s = mid - self.state_model.min_sel_dur_s / 2
            tail_s = mid + self.state_model.min_sel_dur_s / 2
        if head_s < 0:
            head_s = 0
            tail_s = head_s + width
        if tail_s > self.state_model.selected_value.duration_s:
            tail_s = self.state_model.selected_value.duration_s
            head_s = tail_s - width
        assert head_s >= 0
        self.state_model.head_s = head_s
        self.state_model.tail_s = tail_s
        self.head_box.setText(f"{head_s * 1000:.1f}")
        self.tail_box.setText(f"{tail_s * 1000:.1f}")
        self.temporal_view.update_plot(frame=True)

    def move_selection(self, delta_s: float) -> None:
        new_head = self.state_model.head_s + delta_s
        new_tail = self.state_model.tail_s + delta_s
        self.set_selection(new_head, new_tail)
