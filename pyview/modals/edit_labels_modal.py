from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from ..menu.label_menu import LabelMenu
from ..state import Label
from .label_modal import open_label_dialog


def _format_label_row(label: Label) -> str:
    offset_text = f"{label.offset_s * 1000:.1f}"
    return f"{label.name:<14} {offset_text:>10}   {label.note}"


def open_edit_labels_dialog(parent: LabelMenu) -> None:
    dialog = QDialog(parent.root)
    dialog.setWindowTitle("Edit labels")
    dialog.setModal(True)
    dialog.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

    labels = parent.state.labels

    outer_layout = QVBoxLayout(dialog)
    outer_layout.setContentsMargins(12, 12, 12, 12)
    outer_layout.setSpacing(8)

    header_layout = QHBoxLayout()
    header_layout.setContentsMargins(0, 0, 0, 0)
    header_layout.setSpacing(0)

    label_header = QLabel("Label", dialog)
    offset_header = QLabel("Offset", dialog)
    comments_header = QLabel("Comments", dialog)

    label_header.setFixedWidth(120)
    offset_header.setFixedWidth(90)

    label_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
    offset_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
    comments_header.setAlignment(Qt.AlignmentFlag.AlignCenter)

    header_layout.addWidget(label_header)
    header_layout.addWidget(offset_header)
    header_layout.addWidget(comments_header, 1)

    outer_layout.addLayout(header_layout)

    label_list = QListWidget(dialog)
    label_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
    label_list.setFixedSize(330, 170)

    mono_font = QFont("Menlo")
    mono_font.setStyleHint(QFont.StyleHint.Monospace)
    label_list.setFont(mono_font)

    for label in labels:
        item = QListWidgetItem(_format_label_row(label))
        item.setData(Qt.ItemDataRole.UserRole, label)
        label_list.addItem(item)

    outer_layout.addWidget(label_list)

    buttons_layout = QHBoxLayout()
    buttons_layout.setContentsMargins(0, 0, 0, 0)
    buttons_layout.setSpacing(6)
    buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    edit_button = QPushButton("Edit", dialog)
    delete_button = QPushButton("Delete", dialog)
    close_button = QPushButton("Close", dialog)

    buttons_layout.addWidget(edit_button)
    buttons_layout.addWidget(delete_button)
    buttons_layout.addWidget(close_button)

    outer_layout.addLayout(buttons_layout)

    def update_buttons() -> None:
        n_selected = len(label_list.selectedItems())
        edit_button.setEnabled(n_selected == 1)
        delete_button.setEnabled(n_selected > 0)

    def refresh_labels() -> None:
        label_list.clear()
        for label in parent.state.labels:
            item = QListWidgetItem(_format_label_row(label))
            item.setData(Qt.ItemDataRole.UserRole, label)
            label_list.addItem(item)

    def on_edit() -> None:
        if len(label_list.selectedItems()) != 1:
            return
        selected = [index.row() for index in label_list.selectedIndexes()]
        open_label_dialog(parent.root.temporal_view, ("edit", selected[0]))
        refresh_labels()

    def on_delete() -> None:
        # UX only: no actual deletion.
        if not label_list.selectedItems():
            return
        selected = [index.row() for index in label_list.selectedIndexes()]
        deleted = parent.state.delete_labels(selected)
        parent.root.temporal_view.update_plot(labels=deleted)
        refresh_labels()

    def on_close() -> None:
        dialog.accept()

    label_list.itemSelectionChanged.connect(update_buttons)
    label_list.itemDoubleClicked.connect(lambda _item: on_edit())
    edit_button.clicked.connect(on_edit)
    delete_button.clicked.connect(on_delete)
    close_button.clicked.connect(on_close)

    close_button.setDefault(True)
    close_button.setAutoDefault(True)
    edit_button.setAutoDefault(False)
    delete_button.setAutoDefault(False)

    update_buttons()

    dialog.adjustSize()
    dialog.setFixedSize(dialog.sizeHint())

    root_geometry = parent.root.frameGeometry()
    dialog_geometry = dialog.frameGeometry()
    dialog_geometry.moveCenter(root_geometry.center())
    dialog.move(dialog_geometry.topLeft())

    dialog.exec()
