from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

if TYPE_CHECKING:
    from .menu_bar import MenuBar


class DataMenu(QMenu):
    def __init__(self, parent: MenuBar):
        super().__init__("Data", parent)

        self.state_model = parent.state_model
        self.root = parent.root

        self.addAction("Report", parent._todo("Report"))
        self.addAction("Track formants", parent._todo("Track formants"))
        self.addAction("Spectral analysis...", parent._todo("Spectral analysis"))
