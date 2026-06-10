from typing import TYPE_CHECKING, Callable

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt import NavigationToolbar2QT
from matplotlib.figure import Figure, SubFigure
from matplotlib.transforms import Bbox
import pickle
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu, QMainWindow

if TYPE_CHECKING:
    from .menu_bar import MenuBar
    from ..window import VarWindow


class FigureCloneWindow(QMainWindow):
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
        self.figure: Figure = pickle.loads(pickle.dumps(source_figure))
        dpi = self.figure.dpi
        width_px, height_px = source_canvas.get_width_height(physical=False)
        self.figure.set_size_inches(width_px / dpi, height_px / dpi, forward=False)

        self.canvas = FigureCanvasQTAgg(self.figure)
        self.setCentralWidget(self.canvas)

        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.addToolBar(self.toolbar)

        self.resize(width_px, height_px)
        self.canvas.draw_idle()


def _figure_bbox(fig: Figure | SubFigure) -> Bbox:
    positions = [ax.get_position().frozen() for ax in fig.axes if ax.get_visible()]
    if not positions:
        return Bbox.from_extents(0.0, 0.0, 1.0, 1.0)
    return Bbox.union(positions)


def _map_rect_to_unit_subfigure(src: Bbox, src_box: Bbox) -> Bbox:
    x0 = (src.x0 - src_box.x0) / src_box.width
    y0 = (src.y0 - src_box.y0) / src_box.height
    x1 = (src.x1 - src_box.x0) / src_box.width
    y1 = (src.y1 - src_box.y0) / src_box.height
    return Bbox.from_extents(x0, y0, x1, y1)


def _clone_into_fig(source_fig: Figure, target_subfig: SubFigure) -> None:
    cloned_fig: Figure = pickle.loads(pickle.dumps(source_fig))

    src_box = _figure_bbox(cloned_fig)

    for ax in list(cloned_fig.axes):
        if not ax.get_visible():
            continue

        old_pos = ax.get_position().frozen()
        new_pos = _map_rect_to_unit_subfigure(old_pos, src_box).frozen()

        ax.remove()
        ax.set_figure(target_subfig)

        ax.set_axes_locator(None)
        ax.set_in_layout(False)

        target_subfig.add_axes(ax)
        ax.set_position(new_pos, which="both")
        ax.set_navigate(False)


class WindowCloneWindow(QMainWindow):
    def __init__(self, source_window: VarWindow, parent: QMainWindow):
        super().__init__(parent)
        self.setWindowTitle(source_window.windowTitle())

        # Careful: if you use the source_window.figure.dpi, it will have
        # been premultiplied when HiDPI
        dpi = self.screen().logicalDotsPerInch()
        width_px = source_window.width()
        height_px = source_window.height()

        self.figure = Figure(figsize=(width_px / dpi, height_px / dpi), dpi=dpi)

        # Same content grid as the Qt layout, excluding the navbar:
        #
        # left column:  stretch 1
        # right column: stretch 2
        # left vertical split: spatial stretch 1, freq stretch 1
        outer = self.figure.add_gridspec(
            nrows=1,
            ncols=2,
            width_ratios=[1, 2],
            left=0.01,
            right=0.995,
            bottom=0.01,
            top=0.99,
            wspace=0.015,
        )

        left = outer[0, 0].subgridspec(
            nrows=2, ncols=1, height_ratios=[1, 1], hspace=0.02
        )

        spatial_subfig = self.figure.add_subfigure(left[0, 0])
        freq_subfig = self.figure.add_subfigure(left[1, 0])
        temporal_subfig = self.figure.add_subfigure(outer[0, 1])

        _clone_into_fig(source_window.spatial_view.figure, spatial_subfig)
        _clone_into_fig(source_window.freq_domain_view.figure, freq_subfig)
        _clone_into_fig(source_window.temporal_view.figure, temporal_subfig)

        self.canvas = FigureCanvasQTAgg(self.figure)
        self.setCentralWidget(self.canvas)

        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.addToolBar(self.toolbar)

        self.resize(width_px, height_px)
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
        open_figure_menu.addAction("Entire window", self._open_window_clone)
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
        self._temporal_clone_window = FigureCloneWindow(
            self.root.temporal_view.figure,
            self.root.temporal_view.canvas,
            title="Temporal display",
            parent=self.root,
        )
        self._temporal_clone_window.show()

    def _open_spatial_view(self):
        self._spatial_clone_window = FigureCloneWindow(
            self.root.spatial_view.figure,
            self.root.spatial_view.canvas,
            title="Spatial display",
            parent=self.root,
        )
        self._spatial_clone_window.show()

    def _open_window_clone(self):
        self._window_clone_window = WindowCloneWindow(
            source_window=self.root,
            parent=self.root,
        )
        self._window_clone_window.show()
