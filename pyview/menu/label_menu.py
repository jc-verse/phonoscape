from typing import TYPE_CHECKING, cast
from pathlib import Path

from PySide6.QtWidgets import QMenu, QMessageBox, QFileDialog, QInputDialog

if TYPE_CHECKING:
    from .menu_bar import MenuBar
from ..data.parse import import_proc_ctor
from ..state import Label
from ..modals.label_modal import open_label_dialog
from ..modals.edit_labels_modal import open_edit_labels_dialog
from ..lproc.protocol import LabelUpdateResult, LPWindowState


class LabelMenu(QMenu):
    def __init__(self, parent: MenuBar):
        super().__init__("Label", parent)

        self.state = parent.state
        self.root = parent.root

        self.addAction(
            "Make label...",
            lambda: open_label_dialog(
                self.root.temporal_view, ("create", self.state.cursor_s)
            ),
        )
        self.addAction("Edit labels...", lambda: open_edit_labels_dialog(self))
        self.addAction("Clear all labels", self._clear_all_labels, shortcut="Ctrl+Y")
        self.addSeparator()
        self.addAction("Export labels...", self._export_labels, shortcut="Ctrl+9")
        self.addAction("Import labels...", self._import_labels)
        self.addSeparator()
        self.addAction("Save labels...", self._save_labels)
        self.addAction("Load labels...", self._load_labels)
        labeling_behavior_menu = QMenu("Labeling behavior", self)
        self.lproc_name_display = labeling_behavior_menu.addAction(
            self.state.lproc.name
        )
        self.lproc_name_display.setEnabled(False)
        labeling_behavior_menu.addSeparator()

        labeling_behavior_menu.addAction("Clear", parent._todo("Clear"))
        labeling_behavior_menu.addAction(
            "Select...", self._select_lproc, shortcut="Ctrl+K"
        )
        labeling_behavior_menu.addAction("Configure...", parent._todo("Configure..."))
        self.addMenu(labeling_behavior_menu)

    def _clear_all_labels(self) -> None:
        if not self.state.labels:
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

        all_labels = list(range(len(self.state.labels)))
        self.state.lproc.on_clear_labels()
        self.state.labels.clear()
        self.root.temporal_view.update_plot(
            labels=LabelUpdateResult(deleted_labels=all_labels)
        )

    def _labels_to_mview_lab_text(self, labels: list[Label]) -> str:
        lines = ["LABEL\tOFFSET\tNOTE\n"]

        for label in labels:
            lines.append(f"{label.name}\t{label.offset_s * 1000.0:.1f}\t{label.note}\n")

        return "".join(lines)

    def _export_labels(self) -> None:
        labels = self.state.labels
        if not labels:
            return

        file_name, _selected_filter = QFileDialog.getSaveFileName(
            self.root,
            "Save labels as",
            f"{self.state.selected_value.name}.lab",
            "Label files (*.lab);;All files (*)",
        )
        if not file_name:
            return

        path = Path(file_name)
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(self._labels_to_mview_lab_text(labels))

        # Seems unnecessary
        # QMessageBox.information(
        #     self.root, "Labels exported", f"Labels written to:\n{path}"
        # )

    def _import_labels(self) -> None:
        file_name, _selected_filter = QFileDialog.getOpenFileName(
            self.root, "Load labels from", "", "Label files (*.lab);;All files (*)"
        )
        if not file_name:
            return

        path = Path(file_name)

        try:
            result = self.state.lproc.import_labels(path)
            self.state.apply_label_update(result)
            self.root.temporal_view.update_plot(labels=result)
        except Exception:
            QMessageBox.critical(
                self.root,
                "Error importing labels",
                f"Error attempting to read labels from {path.name}",
            )

    def _save_labels(self) -> None:
        labels = list(self.root.state.labels)

        if not labels:
            QMessageBox.information(
                self.root,
                "Save labels",
                "There are no labels to save.",
            )
            return

        key, accepted = QInputDialog.getText(
            self.root,
            "Save labels",
            "Save labels as:",
            text=f"{self.state.selected_value.name}_lbl",
        )

        if not accepted:
            return

        key = key.strip()
        if not key:
            QMessageBox.critical(
                self.root, "Invalid name", "Label set name cannot be empty."
            )
            return

        if key in self.root.state.custom:
            reply = QMessageBox.question(
                self.root,
                "Replace labels",
                f'Replace existing custom entry "{key}"?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.root.state.custom[key] = ("LabelList", labels)

    def _load_labels(self) -> None:
        custom = self.root.state.custom

        label_keys = [key for key, value in custom.items() if value[0] == "LabelList"]

        if not label_keys:
            QMessageBox.information(
                self.root,
                "Load labels",
                "There are no saved label sets.",
            )
            return

        key, accepted = QInputDialog.getItem(
            self.root, "Load labels", "Load labels:", label_keys, 0, False
        )

        if key not in label_keys:
            QMessageBox.critical(
                self.root,
                "Invalid labels",
                f'Custom entry "{key}" is not a label set.',
            )
            return

        if not accepted:
            return

        # In MVIEW, loading replaces current labels
        old_labels = list(range(len(self.state.labels)))
        new_labels = list(cast(list[Label], custom[key][1]))
        self.root.state.labels = new_labels
        self.root.temporal_view.update_plot(
            labels=LabelUpdateResult(
                deleted_labels=old_labels, created_labels=new_labels
            )
        )

    def _select_lproc(self) -> None:
        default_dir = Path(__file__).resolve().parent.parent / "lproc"
        file_name, _selected_filter = QFileDialog.getOpenFileName(
            self.root,
            "Select labeling procedure",
            str(default_dir),
            "Labeling procedures (lp_*.py)",
        )

        if not file_name:
            return

        path = Path(file_name)

        if path.suffix != ".py" or not path.name.startswith("lp_"):
            QMessageBox.critical(
                self.root,
                "Invalid labeling procedure",
                "Choose a Python file named lp_*.py.",
            )
            return

        try:
            lproc_ctor = import_proc_ctor(path, "lp")
            self.state.lproc = lproc_ctor(LPWindowState(self.state))
            self.lproc_name_display.setText(self.state.lproc.name)
        except Exception as exc:
            QMessageBox.critical(
                self.root,
                "Error loading labeling procedure",
                f"Error attempting to load {path.name}:\n{exc}",
            )
