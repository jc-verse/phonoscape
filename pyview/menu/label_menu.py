from typing import TYPE_CHECKING

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QMenu, QMessageBox

if TYPE_CHECKING:
    from .menu_bar import MenuBar
from ..modals.label_modal import open_label_dialog
from ..modals.edit_labels_modal import open_edit_labels_dialog


class LabelMenu(QMenu):
    def __init__(self, parent: MenuBar):
        super().__init__("Label", parent)

        self.state_model = parent.state_model
        self.root = parent.root

        self.addAction(
            "Make label...",
            lambda: open_label_dialog(
                self.root.temporal_view, ("create", self.state_model.cursor_s)
            ),
        )
        self.addAction("Edit labels...", lambda: open_edit_labels_dialog(self))
        self.addAction("Clear all labels", self._clear_all_labels).setShortcut(
            QKeySequence("Ctrl+Y")
        )
        self.addSeparator()
        self.addAction("Export labels...", parent._todo("Export labels..."))
        self.addAction("Import labels...", parent._todo("Import labels..."))
        self.addSeparator()
        self.addAction("Save labels...", parent._todo("Save labels..."))
        self.addAction("Load labels...", parent._todo("Load labels..."))
        self.addAction(
            "Set selection to label pair",
            parent._todo("Set selection to label pair"),
        )
        labeling_behavior_menu = QMenu("Labeling behavior", self)
        labeling_behavior_menu.addAction("Clear", parent._todo("Clear"))
        labeling_behavior_menu.addAction("Select...", parent._todo("Select..."))
        labeling_behavior_menu.addAction("Configure...", parent._todo("Configure..."))
        self.addMenu(labeling_behavior_menu)

    def _clear_all_labels(self) -> None:
        if not self.state_model.labels:
            return
        box = QMessageBox(self)
        box.setWindowTitle("Clear all labels")
        box.setText("Clear all labels?")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        box.setDefaultButton(QMessageBox.StandardButton.No)

        reply = box.exec()

        if reply != QMessageBox.StandardButton.Yes:
            return

        all_labels = [*self.state_model.labels]
        self.state_model.labels.clear()
        self.root.temporal_view.update_plot(labels=all_labels)
