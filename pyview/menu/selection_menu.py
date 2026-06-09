from typing import TYPE_CHECKING

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QMenu

if TYPE_CHECKING:
    from .menu_bar import MenuBar


class SelectionMenu(QMenu):
    def __init__(self, parent: MenuBar):
        super().__init__("Selection", parent)

        self.state = parent.state
        self.root = parent.root

        self.addAction(
            "Set head to cursor", lambda: self.root.set_head(self.state.cursor_s)
        )
        self.addAction(
            "Set tail to cursor", lambda: self.root.set_tail(self.state.cursor_s)
        )
        self.addAction("Set selection to label pair", self._set_sel_to_lbl_pair)
        self.addAction(
            "Reset selection",
            lambda: self.root.set_selection(0.0, self.state.selected_value.duration_s),
        )

        self.addSeparator()
        self.addAction("Shrink selection", self._shrink_selection)
        self.addAction("Expand selection", self._expand_selection)

        self.addSeparator()
        self.addAction(
            "Shift selection left",
            lambda: self.root.move_selection(self.state.head_s - self.state.tail_s),
        ).setShortcut(QKeySequence("Ctrl+L"))
        self.addAction(
            "Shift selection right",
            lambda: self.root.move_selection(self.state.tail_s - self.state.head_s),
        ).setShortcut(QKeySequence("Ctrl+R"))

    def _shrink_selection(self) -> None:
        nudge = 0.1 * (self.state.tail_s - self.state.head_s)
        self.root.set_selection(self.state.head_s + nudge, self.state.tail_s - nudge)

    def _expand_selection(self) -> None:
        nudge = 0.1 * (self.state.tail_s - self.state.head_s)
        self.root.set_selection(self.state.head_s - nudge, self.state.tail_s + nudge)

    def _set_sel_to_lbl_pair(self) -> None:
        labels = sorted(self.state.labels, key=lambda lbl: lbl.offset_s)
        if len(labels) < 2:
            return
        for left, right in zip(labels, labels[1:]):
            if left.offset_s <= self.state.cursor_s <= right.offset_s:
                self.root.set_selection(left.offset_s, right.offset_s)
                return
