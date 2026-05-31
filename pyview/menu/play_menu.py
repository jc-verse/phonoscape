import sys
from typing import TYPE_CHECKING

import tkinter as tk

if TYPE_CHECKING:
    from .menu_bar import MenuBar
from .utils import make_accelerator
from ..state import PyViewState
from ..widgets.play_button import play, modes


class PlayMenu(tk.Menu):
    def __init__(self, parent: MenuBar, state_model: PyViewState):
        super().__init__(parent, tearoff=False)
        self.state_model = state_model
        self.root = parent.parent

        self.add_command(
            label="Play",
            command=self._play,
            accelerator=make_accelerator("P", self.root, self._play),
        )
        self.add_separator()

        for mode in modes:
            self.add_radiobutton(label=mode, variable=state_model.play_mode, value=mode)

    def _play(self):
        play(self.state_model)
