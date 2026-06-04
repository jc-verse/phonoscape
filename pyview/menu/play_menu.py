from typing import TYPE_CHECKING

from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QMenu

if TYPE_CHECKING:
    from .menu_bar import MenuBar

from ..state import PyViewState
from ..widgets.play_button import play, modes


class PlayMenu(QMenu):
    def __init__(self, parent: MenuBar, state_model: PyViewState):
        super().__init__("Play", parent)

        self.state_model = state_model
        self.root = parent.parent

        play_action = QAction("Play", self)
        play_action.setShortcut(QKeySequence("Ctrl+P"))
        play_action.triggered.connect(self._play)
        self.addAction(play_action)
        self.addSeparator()

        self.mode_action_group = QActionGroup(self)
        self.mode_action_group.setExclusive(True)

        current_mode = state_model.play_mode.get()

        for mode in modes:
            action = QAction(mode, self)
            action.setCheckable(True)
            action.setChecked(mode == current_mode)
            action.triggered.connect(
                lambda checked=False, mode=mode: state_model.play_mode.set(mode)
            )

            self.mode_action_group.addAction(action)
            self.addAction(action)

    def _play(self) -> None:
        play(self.state_model)
