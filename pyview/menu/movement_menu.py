from typing import TYPE_CHECKING
from enum import Enum, auto

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QActionGroup
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

        self.state = parent.state
        self.root = parent.root

        self._cycling_mode = CyclingMode.STOPPED
        self._cycling_direction = 0

        self._cycle_timer = QTimer(self)
        # TODO: make this configurable
        self.frame_rate = 50
        self.playback_speed = 1.0
        self._cycle_timer.setInterval(1000 // self.frame_rate)
        self._cycle_timer.timeout.connect(self._cycle_once)

        self.addAction("Step forward", self._step_forward, shortcut="Ctrl+F")
        self.addAction("Step backward", self._step_backward, shortcut="Ctrl+B")
        self.addAction("Shift forward", lambda: self._shift_selection(1))
        self.addAction("Shift backward", lambda: self._shift_selection(-1))
        self.addSeparator()
        cycling_group = QActionGroup(self)
        cycling_group.setExclusive(True)
        forward_action = QAction("Cycle forward", self, checkable=True)
        forward_action.triggered.connect(
            lambda: self._set_cycling_mode(CyclingMode.FORWARD)
        )
        self.forward_action = forward_action
        cycling_group.addAction(forward_action)
        backward_action = QAction("Cycle backward", self, checkable=True)
        backward_action.triggered.connect(
            lambda: self._set_cycling_mode(CyclingMode.BACKWARD)
        )
        self.backward_action = backward_action
        cycling_group.addAction(backward_action)
        reflective_action = QAction("Reflective cycling", self, checkable=True)
        reflective_action.triggered.connect(
            lambda: self._set_cycling_mode(CyclingMode.REFLECTIVE)
        )
        self.reflective_action = reflective_action
        cycling_group.addAction(reflective_action)
        self.addActions(cycling_group.actions())
        self.addAction(
            "Stop cycling",
            lambda: self._set_cycling_mode(CyclingMode.STOPPED),
            shortcut="Ctrl+X",
        )

    def _step_forward(self):
        # TODO: make this configurable
        self.root.set_cursor(self.state.cursor_s + 0.005)

    def _step_backward(self):
        self.root.set_cursor(self.state.cursor_s - 0.005)

    def _shift_selection(self, direction: int) -> None:
        old_head = self.state.head_s
        old_tail = self.state.tail_s
        old_cursor = self.state.cursor_s

        width = old_tail - old_head
        if old_head <= old_cursor <= old_tail:
            cursor_rel = old_cursor - old_head
        else:
            cursor_rel = 0.0

        self.root.move_selection(direction * width)
        self.root.set_cursor(self.state.head_s + cursor_rel)

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

        head = self.state.head_s
        tail = self.state.tail_s
        cursor = self.state.cursor_s

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
