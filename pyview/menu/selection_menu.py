from typing import TYPE_CHECKING

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QMenu

if TYPE_CHECKING:
    from .menu_bar import MenuBar


class SelectionMenu(QMenu):
    def __init__(self, parent: MenuBar):
        super().__init__("Selection", parent)

        self.state_model = parent.state_model
        self.root = parent.root

        self.addAction("Set head to cursor", self._set_head_to_cursor)
        self.addAction("Set tail to cursor", self._set_tail_to_cursor)
        self.addAction("Shrink selection", self._shrink_selection)
        self.addAction("Expand selection", self._expand_selection)

        self.addAction("Shift selection left", self._shift_selection_left).setShortcut(
            QKeySequence("Ctrl+L")
        )

        self.addAction(
            "Shift selection right", self._shift_selection_right
        ).setShortcut(QKeySequence("Ctrl+R"))

        self.addAction("Reset selection", self._reset_selection)

    def _set_head_to_cursor(self) -> None:
        self.state_model.head_s = min(
            self.state_model.cursor_s,
            self.state_model.tail_s - self.state_model.min_sel_dur_s,
        )
        self.root.temporal_view.update_plot(frame=True)

    def _set_tail_to_cursor(self) -> None:
        self.state_model.tail_s = max(
            self.state_model.cursor_s,
            self.state_model.head_s + self.state_model.min_sel_dur_s,
        )
        self.root.temporal_view.update_plot(frame=True)

    def _shrink_selection(self) -> None:
        nudge = 0.1 * (self.state_model.tail_s - self.state_model.head_s)
        new_head = self.state_model.head_s + nudge
        new_tail = self.state_model.tail_s - nudge
        if new_tail - new_head >= self.state_model.min_sel_dur_s:
            self.state_model.head_s = new_head
            self.state_model.tail_s = new_tail
        else:
            mid = (self.state_model.head_s + self.state_model.tail_s) / 2
            self.state_model.head_s = mid - self.state_model.min_sel_dur_s / 2
            self.state_model.tail_s = mid + self.state_model.min_sel_dur_s / 2
        self.root.temporal_view.update_plot(frame=True)

    def _expand_selection(self) -> None:
        nudge = 0.1 * (self.state_model.tail_s - self.state_model.head_s)
        self.state_model.head_s = max(0, self.state_model.head_s - nudge)
        self.state_model.tail_s = min(
            self.state_model.selected_value.duration_s,
            self.state_model.tail_s + nudge,
        )
        self.root.temporal_view.update_plot(frame=True)

    def _shift_selection_left(self) -> None:
        sel_len = self.state_model.tail_s - self.state_model.head_s
        new_head = max(0, self.state_model.head_s - sel_len)
        new_tail = new_head + sel_len
        self.state_model.head_s = new_head
        self.state_model.tail_s = new_tail
        self.root.temporal_view.update_plot(frame=True)

    def _shift_selection_right(self) -> None:
        sel_len = self.state_model.tail_s - self.state_model.head_s
        new_tail = min(
            self.state_model.selected_value.duration_s,
            self.state_model.tail_s + sel_len,
        )
        new_head = new_tail - sel_len
        self.state_model.head_s = new_head
        self.state_model.tail_s = new_tail
        self.root.temporal_view.update_plot(frame=True)

    def _reset_selection(self) -> None:
        self.state_model.head_s = 0.0
        self.state_model.tail_s = self.state_model.selected_value.duration_s
        self.root.temporal_view.update_plot(frame=True)
