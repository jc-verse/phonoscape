from typing import TYPE_CHECKING

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QMenu

if TYPE_CHECKING:
    from .menu_bar import MenuBar


class MovementMenu(QMenu):
    def __init__(self, parent: MenuBar):
        super().__init__("Movement", parent)

        self.state_model = parent.state_model
        self.root = parent.root

        self.addAction("Step forward", parent._todo("Step forward")).setShortcut(
            QKeySequence("Ctrl+F")
        )
        self.addAction("Step backward", parent._todo("Step backward")).setShortcut(
            QKeySequence("Ctrl+B")
        )
        self.addAction("Shift forward", parent._todo("Shift forward"))
        self.addAction("Shift backward", parent._todo("Shift backward"))
        self.addSeparator()
        self.addAction("Reflective cycling", parent._todo("Reflective cycling"))
        self.addAction("Cycle forward", parent._todo("Cycle forward"))
        self.addAction("Cycle backward", parent._todo("Cycle backward"))
        self.addAction("Stop cycling", parent._todo("Stop cycling")).setShortcut(
            QKeySequence("Ctrl+X")
        )
