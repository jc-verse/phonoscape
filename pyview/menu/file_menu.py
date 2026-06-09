from typing import TYPE_CHECKING

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu

if TYPE_CHECKING:
    from .menu_bar import MenuBar


class FileMenu(QMenu):
    def __init__(self, parent: MenuBar):
        super().__init__("File", parent)

        self.state_model = parent.state_model
        self.root = parent.root

        variables_menu = QMenu("Variables", self)
        self.variable_action_group = QActionGroup(self)
        self.variable_action_group.setExclusive(True)

        current_variable = self.state_model.selected_variable

        for name in self.state_model.app_config.data.keys():
            action = QAction(name, self)
            action.setCheckable(True)
            action.setChecked(name == current_variable)
            action.triggered.connect(
                lambda checked=False, name=name: self.root.show_variable(name)
            )

            self.variable_action_group.addAction(action)
            variables_menu.addAction(action)

        self.addMenu(variables_menu)
        self.addSeparator()

        save_menu = QMenu("Save", self)
        save_menu.addAction(
            "Save all but selection...",
            parent._todo("Save all but selection"),
        )
        save_menu.addAction(
            "Save selection only...",
            parent._todo("Save selection only"),
        )

        self.addMenu(save_menu)
        self.addAction("Export...", parent._todo("Export"))
        self.addAction("Close window", self.root.close)
        self.addAction("Close all", self.root.window_manager.close_all)
