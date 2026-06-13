from typing import TYPE_CHECKING

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu

if TYPE_CHECKING:
    from .menu_bar import MenuBar

from ..widgets.play_button import play, modes


class PlayMenu(QMenu):
    def __init__(self, parent: MenuBar):
        super().__init__("Play", parent)

        self.state = parent.state
        self.root = parent.root

        self.addAction("Play", lambda: play(self.state), shortcut="Ctrl+P")
        self.addSeparator()

        self.mode_action_group = QActionGroup(self)
        self.mode_action_group.setExclusive(True)

        current_mode = self.state.play_mode

        for mode in modes:
            action = QAction(mode, self, checkable=True, checked=mode == current_mode)
            action.triggered.connect(
                lambda checked=False, mode=mode: self._set_play_mode(mode)
            )

            self.mode_action_group.addAction(action)
            self.addAction(action)

        self.addSeparator()
        self.addAction(
            "Select playback track...", parent._todo("Select playback track"), shortcut="Ctrl+8"
        )

    def _set_play_mode(self, mode: str) -> None:
        self.state.play_mode = mode
