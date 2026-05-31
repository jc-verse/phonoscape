from typing import TYPE_CHECKING
import tkinter as tk

if TYPE_CHECKING:
    from .menu_bar import MenuBar
from .utils import make_accelerator
from ..state import PyViewState


class SelectionMenu(tk.Menu):
    def __init__(self, parent: MenuBar, state_model: PyViewState):
        super().__init__(parent, tearoff=False)
        self.state_model = state_model
        self.parent = parent
        self.root = parent.parent
        self.add_command(label="Set head to cursor", command=self._set_head_to_cursor)
        self.add_command(label="Set tail to cursor", command=self._set_tail_to_cursor)
        self.add_command(label="Shrink selection", command=self._shrink_selection)
        self.add_command(label="Expand selection", command=self._expand_selection)
        self.add_command(
            label="Shift selection left",
            command=self._shift_selection_left,
            accelerator=make_accelerator(
                "L", self.root, action=self._shift_selection_left
            ),
        )
        self.add_command(
            label="Shift selection right",
            command=self._shift_selection_right,
            accelerator=make_accelerator(
                "R", self.root, action=self._shift_selection_right
            ),
        )
        self.add_command(label="Reset selection", command=self._reset_selection)

    def _set_head_to_cursor(self):
        self.state_model.head_s = min(
            self.state_model.cursor_s,
            self.state_model.tail_s - self.state_model.min_sel_dur_s,
        )
        self.root.temporal_view.update_plot(frame=True)

    def _set_tail_to_cursor(self):
        self.state_model.tail_s = max(
            self.state_model.cursor_s,
            self.state_model.head_s + self.state_model.min_sel_dur_s,
        )
        self.root.temporal_view.update_plot(frame=True)

    def _shrink_selection(self):
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

    def _expand_selection(self):
        nudge = 0.1 * (self.state_model.tail_s - self.state_model.head_s)
        self.state_model.head_s = max(0, self.state_model.head_s - nudge)
        self.state_model.tail_s = min(
            self.state_model.selected_value.duration_s, self.state_model.tail_s + nudge
        )
        self.root.temporal_view.update_plot(frame=True)

    def _shift_selection_left(self):
        sel_len = self.state_model.tail_s - self.state_model.head_s
        new_head = max(0, self.state_model.head_s - sel_len)
        new_tail = new_head + sel_len
        self.state_model.head_s = new_head
        self.state_model.tail_s = new_tail
        self.root.temporal_view.update_plot(frame=True)

    def _shift_selection_right(self):
        sel_len = self.state_model.tail_s - self.state_model.head_s
        new_tail = min(
            self.state_model.selected_value.duration_s,
            self.state_model.tail_s + sel_len,
        )
        new_head = new_tail - sel_len
        self.state_model.head_s = new_head
        self.state_model.tail_s = new_tail
        self.root.temporal_view.update_plot(frame=True)

    def _reset_selection(self):
        self.state_model.head_s = 0.0
        self.state_model.tail_s = self.state_model.selected_value.duration_s
        self.root.temporal_view.update_plot(frame=True)
