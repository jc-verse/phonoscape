from typing import TYPE_CHECKING

import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from ..menu.view_menu import ViewMenu
    from ..views.temporal_view import TemporalView
from ..state import SpatialTrajDisplay


def get_visible_scaling(temporal_view: TemporalView) -> tuple[float, float, float]:
    values = {"movement": [], "velocity": [], "acceleration": []}

    for i, spec in enumerate(temporal_view._get_temp_disp_specs()):
        if not isinstance(spec, SpatialTrajDisplay):
            continue
        data = temporal_view.plotting_data[i][1]
        for j in range(data.shape[1]):
            values[spec.content].append(np.nanmax(data[:, j]) - np.nanmin(data[:, j]))

    fallback = temporal_view.state.common_scaling or (0.0, 0.0, 0.0)

    return (
        max(values["movement"]) * 1.1 if values["movement"] else fallback[0],
        max(values["velocity"]) * 1.1 if values["velocity"] else fallback[1],
        max(values["acceleration"]) * 1.1 if values["acceleration"] else fallback[2],
    )


def open_common_scaling_dialog(parent: ViewMenu) -> None:
    dialog = QDialog(parent.root)
    dialog.setWindowTitle("Set common scaling")
    dialog.setModal(True)
    dialog.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
    dialog.setFixedSize(dialog.sizeHint())

    outer_layout = QVBoxLayout(dialog)
    outer_layout.setContentsMargins(12, 12, 12, 12)
    outer_layout.setSpacing(16)

    main = QFrame(dialog)
    main_layout = QGridLayout(main)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setHorizontalSpacing(6)
    main_layout.setVerticalSpacing(4)

    scaling = parent.state.common_scaling

    mvt_entry = QLineEdit(f"{scaling[0]:.2f}" if scaling is not None else "", main)
    vel_entry = QLineEdit(f"{scaling[1]:.2f}" if scaling is not None else "", main)
    acc_entry = QLineEdit(f"{scaling[2]:.2f}" if scaling is not None else "", main)

    mvt_entry.setFixedWidth(80)
    vel_entry.setFixedWidth(80)
    acc_entry.setFixedWidth(80)

    main_layout.addWidget(
        QLabel("Mvt", main), 0, 0, alignment=Qt.AlignmentFlag.AlignRight
    )
    main_layout.addWidget(mvt_entry, 0, 1)
    main_layout.addWidget(
        QLabel("Vel", main), 0, 2, alignment=Qt.AlignmentFlag.AlignRight
    )
    main_layout.addWidget(vel_entry, 0, 3)
    main_layout.addWidget(
        QLabel("Acc", main), 0, 4, alignment=Qt.AlignmentFlag.AlignRight
    )
    main_layout.addWidget(acc_entry, 0, 5)

    adaptive_checkbox = QCheckBox("Adaptive scaling", main)
    adaptive_checkbox.setChecked(parent.state.common_scaling is None)
    main_layout.addWidget(adaptive_checkbox, 1, 1, 1, 5)

    entries = (mvt_entry, vel_entry, acc_entry)

    def set_entries_enabled(enabled: bool) -> None:
        for entry in entries:
            entry.setEnabled(enabled)

    def populate_entries_from_visible() -> None:
        visible_scaling = get_visible_scaling(parent.root.temporal_view)
        mvt_entry.setText(f"{visible_scaling[0]:.2f}")
        vel_entry.setText(f"{visible_scaling[1]:.2f}")
        acc_entry.setText(f"{visible_scaling[2]:.2f}")

    def on_adaptive_changed(checked: bool) -> None:
        if checked:
            for entry in entries:
                entry.clear()
            set_entries_enabled(False)
        else:
            populate_entries_from_visible()
            set_entries_enabled(True)

    adaptive_checkbox.toggled.connect(on_adaptive_changed)
    on_adaptive_changed(adaptive_checkbox.isChecked())

    outer_layout.addWidget(main)

    buttons = QFrame(dialog)
    buttons_layout = QHBoxLayout(buttons)
    buttons_layout.setContentsMargins(0, 0, 0, 0)
    buttons_layout.setSpacing(6)
    buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    outer_layout.addWidget(buttons)

    def on_ok() -> None:
        if adaptive_checkbox.isChecked():
            parent.state.common_scaling = None
        else:
            try:
                parent.state.common_scaling = (
                    float(mvt_entry.text()),
                    float(vel_entry.text()),
                    float(acc_entry.text()),
                )
            except ValueError:
                return

        parent.root.temporal_view.update_plot(spatial_ylim=True)
        dialog.accept()

    def on_cancel() -> None:
        dialog.reject()

    ok_button = QPushButton("OK", buttons, autoDefault=True, default=True)
    ok_button.clicked.connect(on_ok)
    buttons_layout.addWidget(ok_button)

    cancel_button = QPushButton("Cancel", buttons, autoDefault=False)
    cancel_button.clicked.connect(on_cancel)
    buttons_layout.addWidget(cancel_button)

    dialog.adjustSize()
    dialog.setFixedSize(dialog.sizeHint())

    root_geometry = parent.root.frameGeometry()
    dialog_geometry = dialog.frameGeometry()
    dialog_geometry.moveCenter(root_geometry.center())
    dialog.move(dialog_geometry.topLeft())

    dialog.exec()
