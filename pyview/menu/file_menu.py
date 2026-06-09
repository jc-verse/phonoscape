from typing import TYPE_CHECKING, Callable

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu

if TYPE_CHECKING:
    from .menu_bar import MenuBar


class FileMenu(QMenu):
    def __init__(self, parent: MenuBar):
        super().__init__("File", parent)

        self.state = parent.state
        self.root = parent.root

        if len(self.state.app_config.data) > 1:
            variables_menu = QMenu("Variables", self)
            variables_menu.addAction("Previous", self._open_previous, shortcut="Ctrl+1")
            variables_menu.addAction("Next", self._open_next, shortcut="Ctrl+2")
            variables_menu.addAction(
                "Next; close current",
                lambda: self._open_next(after=self._close_current),
                shortcut="Ctrl+3",
            )
            variables_menu.addAction(
                "Next plus export",
                lambda: self._open_next(after=parent._todo("export")),
                shortcut="Ctrl+4",
            )
            variables_menu.addAction(
                "Next; export, close current",
                lambda: self._open_next(
                    after=[parent._todo("export"), self._close_current]
                ),
                shortcut="Ctrl+5",
            )
            variables_menu.addAction(
                "Next; save labels, close current",
                lambda: self._open_next(
                    after=[parent._todo("save labels"), self._close_current]
                ),
                shortcut="Ctrl+6",
            )
            variables_menu.addAction(
                "Next; export/save labels, close current",
                lambda: self._open_next(
                    after=[parent._todo("export/save labels"), self._close_current]
                ),
                shortcut="Ctrl+7",
            )
            variables_menu.addSeparator()
            self.variable_action_group = QActionGroup(self)
            self.variable_action_group.setExclusive(True)

            current_variable = self.state.selected_variable

            for name in self.state.app_config.data.keys():
                action = QAction(name, self)
                action.setCheckable(True)
                action.setChecked(name == current_variable)
                action.triggered.connect(
                    lambda checked=False, name=name: self.root.window_manager.open_window(
                        name, self.root
                    )
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

    def _open_previous(self):
        names = list(self.state.app_config.data.keys())
        assert self.state.selected_variable in names
        idx = names.index(self.state.selected_variable)
        prev_idx = (idx - 1) % len(names)
        self.root.window_manager.open_window(names[prev_idx], self.root)

    def _open_next(
        self, after: list[Callable[[], None]] | Callable[[], None] | None = None
    ):
        names = list(self.state.app_config.data.keys())
        assert self.state.selected_variable in names
        idx = names.index(self.state.selected_variable)
        next_idx = (idx + 1) % len(names)
        self.root.window_manager.open_window(names[next_idx], self.root)
        if after:
            if isinstance(after, list):
                for func in after:
                    func()
            else:
                after()

    def _close_current(self):
        self.root.window_manager.close_window(self.state.selected_variable)
