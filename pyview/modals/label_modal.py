from typing import TYPE_CHECKING, Literal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from ..views.temporal_view import TemporalView


def open_label_dialog(
    parent: TemporalView,
    action: tuple[Literal["create"], float] | tuple[Literal["edit"], int],
) -> None:
    dialog = QDialog(parent)
    dialog.setWindowTitle(f"{action[0].capitalize()} label")
    dialog.setModal(True)
    dialog.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

    outer_layout = QVBoxLayout(dialog)
    outer_layout.setContentsMargins(12, 12, 12, 12)
    outer_layout.setSpacing(16)

    main_layout = QGridLayout()
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setHorizontalSpacing(6)
    main_layout.setVerticalSpacing(8)

    init_label = parent.state_model.labels[action[1]] if action[0] == "edit" else None
    init_name = init_label.name if init_label else ""
    init_offset_s = (
        init_label.offset_s
        if init_label
        else action[1] if action[0] == "create" else 0.0
    )
    init_note = init_label.note if init_label else ""
    name_entry = QLineEdit(init_name, dialog)
    offset_ms_entry = QLineEdit(f"{init_offset_s * 1000.0:.1f}", dialog)
    note_entry = QLineEdit(init_note, dialog)

    name_entry.setFixedWidth(120)
    offset_ms_entry.setFixedWidth(90)
    note_entry.setFixedWidth(260)

    main_layout.addWidget(
        QLabel("Name:", dialog), 0, 0, alignment=Qt.AlignmentFlag.AlignRight
    )
    main_layout.addWidget(name_entry, 0, 1)

    main_layout.addWidget(
        QLabel("Offset (ms):", dialog), 0, 2, alignment=Qt.AlignmentFlag.AlignRight
    )
    main_layout.addWidget(offset_ms_entry, 0, 3)

    main_layout.addWidget(
        QLabel("Note:", dialog), 1, 0, alignment=Qt.AlignmentFlag.AlignRight
    )
    main_layout.addWidget(note_entry, 1, 1, 1, 3)

    outer_layout.addLayout(main_layout)

    buttons_layout = QHBoxLayout()
    buttons_layout.setContentsMargins(0, 0, 0, 0)
    buttons_layout.setSpacing(6)
    buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    ok_button = QPushButton("OK", dialog)
    cancel_button = QPushButton("Cancel", dialog)

    buttons_layout.addWidget(ok_button)
    buttons_layout.addWidget(cancel_button)

    outer_layout.addLayout(buttons_layout)

    def on_ok() -> None:
        try:
            offset_ms = float(offset_ms_entry.text())
        except ValueError:
            QMessageBox.critical(dialog, "Invalid offset", "Offset must be a number.")
            return

        name = name_entry.text().strip()
        if not name:
            QMessageBox.critical(dialog, "Invalid name", "Name cannot be empty.")
            return

        note = note_entry.text().strip()

        if action[0] == "create":
            new_label = parent.state_model.add_label(name, offset_ms / 1000.0, note)
            parent.update_plot(labels=[new_label])
        else:
            new_label, old_label = parent.state_model.edit_label(
                action[1], name, offset_ms / 1000.0, note
            )
            parent.update_plot(labels=[new_label, old_label])

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

    parent_window = parent.window()
    root_geometry = parent_window.frameGeometry()
    dialog_geometry = dialog.frameGeometry()
    dialog_geometry.moveCenter(root_geometry.center())
    dialog.move(dialog_geometry.topLeft())

    dialog.exec()
