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
    from ..menu.view_menu import ViewMenu


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
    main_layout.setVerticalSpacing(0)

    # TODO: Real state
    scaling = [0.0, 0.0, 0.0]

    mvt_entry = QLineEdit(f"{scaling[0]:.2f}", main)
    vel_entry = QLineEdit(f"{scaling[1]:.2f}", main)
    acc_entry = QLineEdit(f"{scaling[2]:.2f}", main)

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

    outer_layout.addWidget(main)

    buttons = QFrame(dialog)
    buttons_layout = QHBoxLayout(buttons)
    buttons_layout.setContentsMargins(0, 0, 0, 0)
    buttons_layout.setSpacing(6)
    buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    ok_button = QPushButton("OK", buttons)
    cancel_button = QPushButton("Cancel", buttons)

    buttons_layout.addWidget(ok_button)
    buttons_layout.addWidget(cancel_button)

    outer_layout.addWidget(buttons)

    def on_ok() -> None:
        # TODO: Update state
        dialog.accept()

    def on_cancel() -> None:
        dialog.reject()

    ok_button.clicked.connect(on_ok)
    cancel_button.clicked.connect(on_cancel)

    ok_button.setDefault(True)
    ok_button.setAutoDefault(True)
    cancel_button.setAutoDefault(False)

    dialog.adjustSize()
    dialog.setFixedSize(dialog.sizeHint())

    root_geometry = parent.root.frameGeometry()
    dialog_geometry = dialog.frameGeometry()
    dialog_geometry.moveCenter(root_geometry.center())
    dialog.move(dialog_geometry.topLeft())

    dialog.exec()
