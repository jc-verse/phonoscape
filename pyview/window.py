from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QMainWindow,
    QWidget,
    QLineEdit,
    QGridLayout,
    QVBoxLayout,
    QHBoxLayout,
)

from .data.process import analyze_audio
from .menu.menu_bar import MenuBar
from .state import WindowState, AppConfig, TrajDisplay, Color
from .widgets.play_button import PlayButton, modes as play_modes
from .widgets.readout import Readout
from .views.temporal_view import TemporalView
from .views.spatial_view_3d import SpatialView3D
from .views.spatial_view_2d import SpatialView2D
from .views.cursor_spect_view import CursorSpectView
from .views.zoomed_audio_view import ZoomedAudioView


class VarWindow(QMainWindow):
    def __init__(
        self,
        window_manager: WindowManager,
        selected_variable: str,
        temporal_disp_specs: list[TrajDisplay],
        colors: dict[str, Color],
        app_config: AppConfig,
        view: tuple[float, float, float],
        head_s: float,
        tail_s: float,
        custom: dict[str, Any],
    ):
        super().__init__()
        window_manager.add_window(selected_variable, self)
        self.window_manager = window_manager
        self.state = WindowState(
            custom=custom,
            labels=[],
            selected_variable=selected_variable,
            temporal_disp_specs=temporal_disp_specs,
            colors=colors,
            app_config=app_config,
            view=view,
            common_scaling=None,
            cursor_s=0.0,
            head_s=head_s,
            tail_s=tail_s,
            play_mode=play_modes[0],
        )
        if self.state.app_config.audio_traj:
            self.state.selected_value.audio_traj = analyze_audio(
                self.state.selected_value.trajectories[
                    self.state.app_config.audio_traj
                ],
                self.state.app_config,
            )

        self.setWindowTitle(f"PyView - {app_config.file.name} - {selected_variable}")
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
            f"{self.state.selected_variable} "
            f"({self.state.selected_value.duration_s:.2f}s)",
            navbar,
        )
        navbar_layout.addWidget(self.info_label)

        if self.state.app_config.audio_traj is not None:
            play_button = PlayButton(navbar, self.state)
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
            box.returnPressed.connect(lambda: callback(float(box.text()) / 1000))

            label.setBuddy(box)

            group_layout.addWidget(label)
            group_layout.addWidget(box)

            navbar_layout.addWidget(group)

            return box

        self.cursor_box = add_navbar_time_box(
            "Cursor", self.state.cursor_s * 1000, self.set_cursor
        )
        self.head_box = add_navbar_time_box(
            "Head", self.state.head_s * 1000, self.set_head
        )
        self.tail_box = add_navbar_time_box(
            "Tail", self.state.tail_s * 1000, self.set_tail
        )

        navbar_layout.addStretch(1)

        left = QFrame(central)
        left_layout = QGridLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        left_layout.setRowStretch(0, 10)
        left_layout.setRowStretch(1, 7)
        left_layout.setRowStretch(2, 3)
        left_layout.setColumnStretch(0, 1)
        left_layout.setColumnStretch(1, 1)

        root_layout.addWidget(left, 1, 0)

        if self.state.app_config.dimensions == 3:
            self.spatial_view = SpatialView3D(left, state=self.state)
        else:
            self.spatial_view = SpatialView2D(left, state=self.state)
        left_layout.addWidget(self.spatial_view, 0, 0, 1, 2)

        self.cursor_spect_view = CursorSpectView(left, state=self.state)
        left_layout.addWidget(self.cursor_spect_view, 1, 0, 1, 2)

        self.readout = Readout(left, state=self.state)
        left_layout.addWidget(self.readout, 2, 0, 1, 1)

        self.zoomed_audio_view = ZoomedAudioView(left, state=self.state)
        left_layout.addWidget(self.zoomed_audio_view, 2, 1, 1, 1)

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

    def closeEvent(self, event) -> None:
        self.window_manager.remove_window(self.state.selected_variable)
        super().closeEvent(event)

    def set_cursor(self, cursor_s: float, keep_readout=False) -> None:
        cursor_s = min(max(0, cursor_s), self.state.selected_value.duration_s)
        self.state.cursor_s = cursor_s
        self.cursor_box.setText(f"{cursor_s * 1000:.1f}")
        self.temporal_view.update_plot(cursor=True)
        self.spatial_view.update_plot(cursor=True)
        if self.state.app_config.audio_traj is not None:
            self.cursor_spect_view.update_plot(cursor=True)
            self.zoomed_audio_view.update_plot(cursor=True)
        if not keep_readout:
            self.readout.clear_readout()

    def set_head(self, head_s: float) -> None:
        head_s = min(self.state.tail_s - self.state.min_sel_dur_s, head_s)
        self.state.head_s = head_s
        self.head_box.setText(f"{head_s * 1000:.1f}")
        self.temporal_view.update_plot(frame=True)
        self.spatial_view.update_plot(frame=True)

    def set_tail(self, tail_s: float) -> None:
        tail_s = max(self.state.head_s + self.state.min_sel_dur_s, tail_s)
        self.state.tail_s = tail_s
        self.tail_box.setText(f"{tail_s * 1000:.1f}")
        self.temporal_view.update_plot(frame=True)
        self.spatial_view.update_plot(frame=True)

    def set_selection(self, head_s: float, tail_s: float) -> None:
        width = tail_s - head_s
        if width < self.state.min_sel_dur_s:
            mid = (head_s + tail_s) / 2
            head_s = mid - self.state.min_sel_dur_s / 2
            tail_s = mid + self.state.min_sel_dur_s / 2
        if width > self.state.selected_value.duration_s:
            head_s = 0
            tail_s = self.state.selected_value.duration_s
        if head_s < 0:
            head_s = 0
            tail_s = head_s + width
        if tail_s > self.state.selected_value.duration_s:
            tail_s = self.state.selected_value.duration_s
            head_s = tail_s - width
        assert head_s >= 0
        self.state.head_s = head_s
        self.state.tail_s = tail_s
        self.head_box.setText(f"{head_s * 1000:.1f}")
        self.tail_box.setText(f"{tail_s * 1000:.1f}")
        self.temporal_view.update_plot(frame=True)
        self.spatial_view.update_plot(frame=True)

    def move_selection(self, delta_s: float) -> None:
        new_head = self.state.head_s + delta_s
        new_tail = self.state.tail_s + delta_s
        self.set_selection(new_head, new_tail)


class WindowManager:
    def __init__(self):
        self.windows: dict[str, VarWindow] = {}

    def open_window(self, name: str, parent_window: VarWindow) -> None:
        if name in self.windows:
            self.windows[name].raise_()
            self.windows[name].activateWindow()
            return
        selected_value = parent_window.state.app_config.data[name]

        new_tail = min(parent_window.state.tail_s, selected_value.duration_s)
        new_head = min(
            parent_window.state.head_s,
            max(0, new_tail - parent_window.state.min_sel_dur_s),
        )

        # Lazily analyze audio
        if (
            parent_window.state.app_config.audio_traj is not None
            and selected_value.audio_traj is None
        ):
            selected_value.audio_traj = analyze_audio(
                selected_value.trajectories[parent_window.state.app_config.audio_traj],
                parent_window.state.app_config,
            )

        window = VarWindow(
            window_manager=self,
            selected_variable=name,
            temporal_disp_specs=parent_window.state.temporal_disp_specs,
            colors={
                k: selected_value.trajectories[k].color or v
                for k, v in parent_window.state.colors.items()
            },
            app_config=parent_window.state.app_config,
            view=parent_window.state.view,
            head_s=new_head,
            tail_s=new_tail,
            custom=parent_window.state.custom,
        )

        window.show()

    def add_window(self, name: str, window: VarWindow) -> None:
        self.windows[name] = window

    def remove_window(self, name: str) -> None:
        if name in self.windows:
            del self.windows[name]

    def close_window(self, name: str) -> None:
        if name in self.windows:
            # Automatically unregisters itself
            self.windows[name].close()

    def close_all(self) -> None:
        for window in self.windows.values():
            window.close()
