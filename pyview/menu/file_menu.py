from typing import TYPE_CHECKING, Callable

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt import NavigationToolbar2QT
from matplotlib.figure import Figure
import pickle
from PySide6.QtCore import QSize
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu, QMainWindow, QSizePolicy

if TYPE_CHECKING:
    from .menu_bar import MenuBar


class FigureCanvasWithInitialSize(FigureCanvasQTAgg):
    def __init__(self, figure, initial_size: QSize):
        super().__init__(figure)
        self._initial_size = initial_size
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def sizeHint(self) -> QSize:
        return self._initial_size


class MatplotlibCloneWindow(QMainWindow):
    def __init__(
        self,
        source_figure: Figure,
        source_canvas: FigureCanvasQTAgg,
        title: str,
        parent: QMainWindow,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)

        # TODO: not getting the right dimensions
        self.figure = pickle.loads(pickle.dumps(source_figure))
        dpi = self.figure.dpi
        width_px, height_px = source_canvas.get_width_height(physical=False)
        self.figure.set_size_inches(width_px / dpi, height_px / dpi, forward=False)

        self.canvas = FigureCanvasWithInitialSize(
            self.figure, QSize(width_px, height_px)
        )
        self.setCentralWidget(self.canvas)

        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.addToolBar(self.toolbar)

        self.adjustSize()
        self.canvas.draw_idle()


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
                action = QAction(
                    name, self, checkable=True, checked=name == current_variable
                )
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
        open_figure_menu = QMenu("Open figure", self)
        open_figure_menu.addAction("Temporal view", self._open_temporal_view)
        open_figure_menu.addAction("Spatial view", self._open_spatial_view)
        open_figure_menu.addSeparator()
        open_figure_menu.addAction("Entire window", parent._todo("Open entire window"))
        self.addMenu(open_figure_menu)
        self.addSeparator()
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

    def _open_temporal_view(self):
        self._temporal_clone_window = MatplotlibCloneWindow(
            self.root.temporal_view.figure,
            self.root.temporal_view.canvas,
            title="Temporal Display",
            parent=self.root,
        )
        self._temporal_clone_window.show()

    def _open_spatial_view(self):
        self._spatial_clone_window = MatplotlibCloneWindow(
            self.root.spatial_view.figure,
            self.root.spatial_view.canvas,
            title="Spatial Display",
            parent=self.root,
        )
        self._spatial_clone_window.show()
