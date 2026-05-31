import sys
from typing import Callable
import tkinter as tk


def make_accelerator(key: str, root: tk.Tk, action: Callable[[], None]):
    for modifier in ("Control", "Command", "Meta"):
        if sys.platform == "darwin" and modifier == "Control":
            continue
        for button in (key.lower(), key.upper()):
            # TODO: idk why it has to be like this
            root.bind(f"<{modifier}-{button}>", lambda _: action())
    return f"{"Command" if sys.platform == "darwin" else "Ctrl"}+{key.upper()}"
