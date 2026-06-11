from typing import TYPE_CHECKING

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
    from ..menu.view_menu import ViewMenu


views = {
    "2D view (1)": (90, 0, 90),
    "2D view (2)": (0, -90, 0),
    "2D view (3)": (0, -180, 0),
    "3D view (1)": (18, 20, 0),
    "3D view (2)": (-30, -62.5, 0),
    "3D view (3)": (-20, -117, 0),
}


def open_spatial_view_dialog(parent: ViewMenu) -> None:
    dialog = QDialog(parent.root)
    dialog.setWindowTitle("Specify view")
    dialog.setModal(True)
    dialog.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

    outer_layout = QVBoxLayout(dialog)
    outer_layout.setContentsMargins(12, 12, 12, 12)
    outer_layout.setSpacing(12)

    main_layout = QGridLayout()
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setHorizontalSpacing(8)
    main_layout.setVerticalSpacing(8)

    azim_entry = QLineEdit(str(parent.root.spatial_view.ax.azim), dialog)
    elev_entry = QLineEdit(str(parent.root.spatial_view.ax.elev), dialog)
    roll_entry = QLineEdit(str(parent.root.spatial_view.ax.roll), dialog)

    azim_entry.setFixedWidth(100)
    elev_entry.setFixedWidth(100)
    roll_entry.setFixedWidth(100)

    main_layout.addWidget(
        QLabel("azim", dialog), 0, 0, alignment=Qt.AlignmentFlag.AlignRight
    )
    main_layout.addWidget(azim_entry, 0, 1)

    main_layout.addWidget(
        QLabel("elev", dialog), 1, 0, alignment=Qt.AlignmentFlag.AlignRight
    )
    main_layout.addWidget(elev_entry, 1, 1)

    main_layout.addWidget(
        QLabel("roll", dialog), 2, 0, alignment=Qt.AlignmentFlag.AlignRight
    )
    main_layout.addWidget(roll_entry, 2, 1)

    outer_layout.addLayout(main_layout)

    buttons_layout = QHBoxLayout()
    buttons_layout.setContentsMargins(0, 0, 0, 0)
    buttons_layout.setSpacing(6)
    buttons_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

    def on_ok() -> None:
        try:
            azim = float(azim_entry.text())
            elev = float(elev_entry.text())
            roll = float(roll_entry.text())
        except ValueError:
            QMessageBox.critical(
                dialog, "Invalid view", "azim, elev, and roll must be numbers."
            )
            return

        dialog.accept()

        matching_view = None
        for label, (velev, vazim, vroll) in views.items():
            if azim == vazim and elev == velev and roll == vroll:
                matching_view = label
                break

        if matching_view is not None:
            parent._set_view_option(matching_view)
        else:
            parent._clear_view_selection()
            parent.root.spatial_view.ax.view_init(elev=elev, azim=azim, roll=roll)
            parent.root.spatial_view.canvas.draw_idle()

    def on_cancel() -> None:
        dialog.reject()

    ok_button = QPushButton("OK", dialog, autoDefault=True, default=True)
    ok_button.clicked.connect(on_ok)
    buttons_layout.addWidget(ok_button)

    cancel_button = QPushButton("Cancel", dialog, autoDefault=False)
    cancel_button.clicked.connect(on_cancel)
    buttons_layout.addWidget(cancel_button)

    outer_layout.addLayout(buttons_layout)

    dialog.adjustSize()
    dialog.setFixedSize(dialog.sizeHint())

    root_geometry = parent.root.frameGeometry()
    dialog_geometry = dialog.frameGeometry()
    dialog_geometry.moveCenter(root_geometry.center())
    dialog.move(dialog_geometry.topLeft())

    dialog.exec()
