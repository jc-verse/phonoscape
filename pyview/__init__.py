import sys
from pathlib import Path
from typing import cast, Literal, Unpack

import matplotlib.pyplot as plt
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QMainWindow, QWidget
from PySide6.QtWidgets import QGridLayout, QVBoxLayout, QHBoxLayout

from .data.parse import load_variables, normalize_args, PyViewArgs
from .data.process import get_plotting_data
from .menu.menu_bar import MenuBar
from .state import PyViewState, ScalarTrajDisplay, StringVar
from .widgets.play_button import PlayButton, modes as play_modes
from .views.temporal_view import TemporalView
from .views.spatial_view_3d import SpatialView3D
from .views.spatial_view_2d import SpatialView2D
from .views.freq_domain_view import FreqDomainView


class PyViewQt(QMainWindow):
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

        screen = QApplication.primaryScreen()
        dpi = screen.logicalDotsPerInch() if screen is not None else 96.0

        self.state_model = PyViewState(
            file=path,
            variables_pattern=variables,
            data=data,
            other_data=other_data,
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
            dpi=dpi,
            dimensions=cast(Literal[2, 3], dimensions),
            spatial_bounds=(
                (min_x, max_x, min_y, max_y, min_z, max_z)
                if dimensions == 3
                else (min_x, max_x, min_y, max_y)
            ),
            config=config,
            cursor_s=0.0,
            head_s=0.0,
            tail_s=data[selected_variable].duration_s,
            play_mode=StringVar(value=play_modes[0]),
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

        if self.state_model.config.audio_traj is not None:
            play_button = PlayButton(navbar, self.state_model)
            navbar_layout.addWidget(play_button)

        self.info_label = QLabel(
            f"{self.state_model.selected_variable} "
            f"({self.state_model.data[self.state_model.selected_variable].duration_s:.2f}s)",
            navbar,
        )
        navbar_layout.addWidget(self.info_label)
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

        self.temporal_view = TemporalView(
            right,
            state_model=self.state_model,
            on_cursor_change=self._on_cursor_change,
        )
        right_layout.addWidget(self.temporal_view, stretch=1)

        # Important: create menu bar after views, because it directly manipulates them.
        self.selected_variable_var = StringVar(value=self.state_model.selected_variable)
        self.menu_bar = MenuBar(self, self.state_model)
        self.setMenuBar(self.menu_bar)

    def _on_cursor_change(self) -> None:
        self.spatial_view.update_plot(points=True)
        if self.state_model.config.audio_traj is not None:
            self.freq_domain_view.update_plot()


def pyview(file: str, variables: str = "*", **kwargs: Unpack[PyViewArgs]) -> None:
    app = QApplication.instance()
    owns_app = app is None

    if app is None:
        app = QApplication(sys.argv)

    window = PyViewQt(file, variables, **kwargs)
    window.show()

    if owns_app:
        sys.exit(app.exec())
