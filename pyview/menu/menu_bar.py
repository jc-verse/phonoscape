from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenuBar

from .file_menu import FileMenu
from .data_menu import DataMenu
from .view_menu import ViewMenu
from .play_menu import PlayMenu
from .selection_menu import SelectionMenu
from .movement_menu import MovementMenu
from .label_menu import LabelMenu

if TYPE_CHECKING:
    from .. import VarWindow


class MenuBar(QMenuBar):
    def __init__(self, parent: VarWindow) -> None:
        super().__init__(parent)

        self.root = parent
        self.state = parent.state

        self.addMenu(FileMenu(self))
        self.addMenu(DataMenu(self))
        self.addMenu(ViewMenu(self))
        self.addMenu(PlayMenu(self))
        self.addMenu(SelectionMenu(self))
        self.addMenu(MovementMenu(self))
        self.addMenu(LabelMenu(self))

    def _todo(self, action: str):
        return lambda: print(f"TODO: {action}")
