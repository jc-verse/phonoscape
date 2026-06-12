from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from ..menu.movement_menu import MovementMenu


def open_movement_config_dialog(parent: MovementMenu) -> None:
    config = parent.state.app_config

    dialog = QDialog(parent.root)
    dialog.setWindowTitle("Movement config")
    dialog.setModal(True)
    dialog.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

    outer_layout = QVBoxLayout(dialog)
    outer_layout.setContentsMargins(12, 12, 12, 12)
    outer_layout.setSpacing(16)

    main = QFrame(dialog)
    main_layout = QGridLayout(main)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setHorizontalSpacing(8)
    main_layout.setVerticalSpacing(8)
    outer_layout.addWidget(main)

    nudge_step_ms_field = QLineEdit(f"{config.nudge_step_ms:g}", main)
    playback_rate_field = QLineEdit(f"{config.playback_rate:g}", main)

    fields = [
        ("Nudge step size (ms)", nudge_step_ms_field),
        ("Playback rate", playback_rate_field),
    ]

    for row, (label_text, field) in enumerate(fields):
        label = QLabel(label_text, main)
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        label.setBuddy(field)
        field.setFixedWidth(90)
        main_layout.addWidget(label, row, 0)
        main_layout.addWidget(field, row, 1)

    buttons = QFrame(dialog)
    button_layout = QHBoxLayout(buttons)
    button_layout.setContentsMargins(0, 0, 0, 0)
    button_layout.addStretch()

    ok_button = QPushButton("OK", buttons)
    cancel_button = QPushButton("Cancel", buttons)
    button_layout.addWidget(ok_button)
    button_layout.addWidget(cancel_button)
    outer_layout.addWidget(buttons)

    def parse_positive_float(field: QLineEdit, fallback: float) -> float:
        try:
            value = float(field.text())
        except ValueError:
            return fallback
        if value <= 0:
            return fallback
        return value

    def accept() -> None:
        parent.state.app_config.nudge_step_ms = parse_positive_float(
            nudge_step_ms_field, config.nudge_step_ms
        )
        parent.state.app_config.playback_rate = parse_positive_float(
            playback_rate_field, config.playback_rate
        )
        dialog.accept()

    ok_button.clicked.connect(accept)
    cancel_button.clicked.connect(dialog.reject)

    dialog.setFixedSize(dialog.sizeHint())
    dialog.exec()
