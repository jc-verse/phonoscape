from typing import TYPE_CHECKING, cast
from pathlib import Path
import re

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QMenu, QMessageBox, QFileDialog, QInputDialog

if TYPE_CHECKING:
    from .menu_bar import MenuBar
from ..state import Label
from ..modals.label_modal import open_label_dialog
from ..modals.edit_labels_modal import open_edit_labels_dialog

_MVIEW_IMPORT_ROW_RE = re.compile(r"(\w*)\s+([0-9.]+)")
_MVIEW_IMPORT_HEADER_RE = re.compile(r"(\w+)")


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
        self.addAction("Clear all labels", self._clear_all_labels).setShortcut(
            QKeySequence("Ctrl+Y")
        )
        self.addSeparator()
        self.addAction("Export labels...", self._export_labels)
        self.addAction("Import labels...", self._import_labels)
        self.addSeparator()
        self.addAction("Save labels...", self._save_labels)
        self.addAction("Load labels...", self._load_labels)
        labeling_behavior_menu = QMenu("Labeling behavior", self)
        labeling_behavior_menu.addAction("Clear", parent._todo("Clear"))
        labeling_behavior_menu.addAction("Select...", parent._todo("Select..."))
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

        all_labels = [*self.state.labels]
        self.state.labels.clear()
        self.root.temporal_view.update_plot(labels=all_labels)

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
            with path.open("r", encoding="utf-8", newline=None) as f:
                lines = f.read().splitlines()

            # MVIEW expects lines{1}; an empty file falls into the catch branch.
            header_tokens = _MVIEW_IMPORT_HEADER_RE.findall(lines[0])
            if (
                len(header_tokens) < 2
                or header_tokens[0] != "LABEL"
                or header_tokens[1] != "OFFSET"
            ):
                raise ValueError("unrecognized format")

            imported_labels: list[Label] = []

            for line in lines[1:]:
                match = _MVIEW_IMPORT_ROW_RE.search(line)
                if match is None:
                    continue

                name = match.group(1)
                offset_ms_text = match.group(2)
                offset_ms = float(offset_ms_text)
                offset_s = offset_ms / 1000.0

                # MVIEW import sets HOOK = [], i.e. it does not preserve NOTE.
                imported_labels.append(
                    self.state.add_label(name=name, offset_s=offset_s, note="")
                )

            if imported_labels:
                self.root.temporal_view.update_plot(labels=imported_labels)
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
        old_labels = list(self.root.state.labels)
        new_labels = list(cast(list[Label], custom[key][1]))

        self.root.state.labels = new_labels

        changed_labels = old_labels + [
            label for label in new_labels if label not in old_labels
        ]
        self.root.temporal_view.update_plot(labels=changed_labels)
