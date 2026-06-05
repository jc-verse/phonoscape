from typing import TYPE_CHECKING
from enum import Enum, auto

from PySide6.QtCore import QTimer
from PySide6.QtGui import QKeySequence, QAction, QActionGroup
from PySide6.QtWidgets import QMenu

if TYPE_CHECKING:
    from .menu_bar import MenuBar


class CyclingMode(Enum):
    STOPPED = auto()
    FORWARD = auto()
    BACKWARD = auto()
    REFLECTIVE = auto()


class MovementMenu(QMenu):
    def __init__(self, parent: MenuBar):
        super().__init__("Movement", parent)

        self.state_model = parent.state_model
        self.root = parent.root

        self._cycling_mode = CyclingMode.STOPPED
        self._cycling_direction = 0

        self._cycle_timer = QTimer(self)
        # TODO: make this configurable
        self.frame_rate = 50
        self.playback_speed = 1.0
        self._cycle_timer.setInterval(1000 // self.frame_rate)
        self._cycle_timer.timeout.connect(self._cycle_once)

        self.addAction("Step forward", self._step_forward).setShortcut(
            QKeySequence("Ctrl+F")
        )
        self.addAction("Step backward", self._step_backward).setShortcut(
            QKeySequence("Ctrl+B")
        )
        self.addAction("Shift forward", lambda: self._shift_selection(1))
        self.addAction("Shift backward", lambda: self._shift_selection(-1))
        self.addSeparator()
        cycling_group = QActionGroup(self)
        cycling_group.setExclusive(True)
        forward_action = QAction("Cycle forward", self)
        forward_action.setCheckable(True)
        forward_action.triggered.connect(
            lambda: self._set_cycling_mode(CyclingMode.FORWARD)
        )
        self.forward_action = forward_action
        cycling_group.addAction(forward_action)
        backward_action = QAction("Cycle backward", self)
        backward_action.setCheckable(True)
        backward_action.triggered.connect(
            lambda: self._set_cycling_mode(CyclingMode.BACKWARD)
        )
        self.backward_action = backward_action
        cycling_group.addAction(backward_action)
        reflective_action = QAction("Reflective cycling", self)
        reflective_action.setCheckable(True)
        reflective_action.triggered.connect(
            lambda: self._set_cycling_mode(CyclingMode.REFLECTIVE)
        )
        self.reflective_action = reflective_action
        cycling_group.addAction(reflective_action)
        self.addActions(cycling_group.actions())
        self.addAction(
            "Stop cycling", lambda: self._set_cycling_mode(CyclingMode.STOPPED)
        ).setShortcut(QKeySequence("Ctrl+X"))

    def _step_forward(self):
        # TODO: make this configurable
        self.root.set_cursor(
            min(
                self.state_model.cursor_s + 0.005,
                self.state_model.selected_value.duration_s,
            )
        )

    def _step_backward(self):
        self.root.set_cursor(max(self.state_model.cursor_s - 0.005, 0))

    def _shift_selection(self, direction: int) -> None:
        old_head = self.state_model.head_s
        old_tail = self.state_model.tail_s
        old_cursor = self.state_model.cursor_s

        width = old_tail - old_head
        if old_head <= old_cursor <= old_tail:
            cursor_rel = old_cursor - old_head
        else:
            cursor_rel = 0.0

        if direction < 0:
            new_head = max(0.0, old_head - width)
            new_tail = new_head + width
        else:
            new_tail = min(self.state_model.selected_value.duration_s, old_tail + width)
            new_head = new_tail - width

        self.state_model.head_s = new_head
        self.state_model.tail_s = new_tail

        self.root.set_cursor(new_head + cursor_rel)
        self.root.temporal_view.update_plot(frame=True)

    def _set_cycling_mode(self, mode: CyclingMode) -> None:
        self._cycling_mode = mode

        match mode:
            case CyclingMode.FORWARD:
                self._cycling_direction = 1
            case CyclingMode.BACKWARD:
                self._cycling_direction = -1
            case CyclingMode.REFLECTIVE:
                self._cycling_direction = 1
            case CyclingMode.STOPPED:
                self._cycling_direction = 0

        self.forward_action.setChecked(mode is CyclingMode.FORWARD)
        self.backward_action.setChecked(mode is CyclingMode.BACKWARD)
        self.reflective_action.setChecked(mode is CyclingMode.REFLECTIVE)

        if mode is CyclingMode.STOPPED:
            self._cycle_timer.stop()
        elif not self._cycle_timer.isActive():
            self._cycle_timer.start()

    def _cycle_once(self) -> None:
        if self._cycling_mode is CyclingMode.STOPPED or self._cycling_direction == 0:
            self._cycle_timer.stop()
            return

        head = self.state_model.head_s
        tail = self.state_model.tail_s
        cursor = self.state_model.cursor_s

        step_s = (1000 // self.frame_rate) / 1000 * self.playback_speed
        new_cursor = cursor + step_s * self._cycling_direction

        if new_cursor < head:
            if self._cycling_mode is CyclingMode.REFLECTIVE:
                self._cycling_direction *= -1
                new_cursor = head
            else:
                new_cursor = tail

        elif new_cursor > tail:
            if self._cycling_mode is CyclingMode.REFLECTIVE:
                self._cycling_direction *= -1
                new_cursor = tail
            else:
                new_cursor = head

        self.root.set_cursor(new_cursor)
