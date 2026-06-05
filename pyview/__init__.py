import sys
from typing import Unpack
from PySide6.QtWidgets import QApplication
from .data.parse import PyViewArgs
from .window import PyViewWindow


def pyview(file: str, variables: str = "*", **kwargs: Unpack[PyViewArgs]) -> None:
    app = QApplication.instance()
    owns_app = app is None

    if app is None:
        app = QApplication(sys.argv)

    window = PyViewWindow(file, variables, **kwargs)
    window.show()

    if owns_app:
        sys.exit(app.exec())
