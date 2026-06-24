from typing import Protocol, Unpack, TypedDict, Any
from enum import Enum, auto
from dataclasses import dataclass, field
from pathlib import Path
import re

from matplotlib.artist import Artist
from matplotlib.axes import Axes

from ..state import Label, WindowState, TrajDisplay


class LPWindowState:
    """
    An immutable view of the current window state, with only certain properties
    exposed to the label procedure.
    The labeling procedure can still access the full state, but it's strongly
    discouraged.
    """

    def __init__(self, state: WindowState):
        self._state = state

    @property
    def selected_value(self):
        return self._state.selected_value

    @property
    def selected_variable(self):
        return self._state.selected_variable

    @property
    def cursor_s(self):
        return self._state.cursor_s

    @property
    def head_s(self):
        return self._state.head_s

    @property
    def tail_s(self):
        return self._state.tail_s

    @property
    def temporal_displays(self):
        return tuple(self._state.temporal_disp_specs)

    @property
    def colors(self):
        return self._state.colors

    @property
    def labels(self):
        return tuple(self._state.labels)


class ConfigureResult(Enum):
    CANCELLED = auto()
    APPLIED = auto()
    APPLIED_AND_REPLOT = auto()
    APPLIED_AND_INVOKE = auto()


@dataclass
class RenderedLabel:
    artists: list[Artist]
    hit_test_artists: list[Artist]


@dataclass
class LabelUpdateResult:
    # Will be added to the end of the label list
    created_labels: list[Label] = field(default_factory=list)
    # Indices in the **original** label list
    deleted_labels: list[int] = field(default_factory=list)
    # Indices in the **original** label list
    edited_labels: dict[int, Label] = field(default_factory=dict)


# Exactly the same as Label
class LabelEdit(TypedDict, total=False):
    name: str
    offset_s: float
    note: str
    color: str
    lproc_data: Any


@dataclass
class LabelPlotContext:
    ax: Axes
    ax_index: int
    spec: TrajDisplay

    def plot_default(self, label: Label) -> RenderedLabel:
        artist = self.ax.axvline(
            label.offset_s,
            color=label.color,
            linewidth=0.8,
            zorder=999,
            clip_on=True,
        )
        artists: list[Artist] = [artist]
        # Only plot label for framing and first real data trajectory
        if self.ax_index == 0 or self.ax_index == 1:
            text = self.ax.text(
                label.offset_s,
                0.98,
                label.name,
                ha="left",
                va="top",
                color=label.color,
                zorder=999,
                clip_on=False,
                transform=self.ax.get_xaxis_transform(),
            )
            artists.append(text)
        return RenderedLabel(artists=artists, hit_test_artists=[artist])


_MVIEW_IMPORT_ROW_RE = re.compile(r"(\w*)\s+([0-9.]+)")
_MVIEW_IMPORT_HEADER_RE = re.compile(r"(\w+)")


class LabelProcedure(Protocol):
    name: str
    state: LPWindowState

    def __init__(self, state: LPWindowState) -> None:
        self.name = "<Unnamed>"
        self.state = state

    def plot_label(self, label: Label, context: LabelPlotContext) -> RenderedLabel:
        return context.plot_default(label)

    def create_label(self, label: Label) -> LabelUpdateResult:
        return LabelUpdateResult(created_labels=[label])

    def edit_label(
        self, label_idx: int, **kwargs: Unpack[LabelEdit]
    ) -> LabelUpdateResult:
        old_label = self.state.labels[label_idx]
        new_label = Label(**{**vars(old_label), **kwargs})
        return LabelUpdateResult(edited_labels={label_idx: new_label})

    def delete_labels(self, labels: list[int]) -> LabelUpdateResult:
        return LabelUpdateResult(deleted_labels=labels)

    def on_clear_labels(self) -> None:
        """
        Cleanup handler when all labels are cleared. This is called **before**
        the labels are actually cleared from the state, so the procedure can still
        access the labels if needed. It does not return anything, so it cannot
        prevent the clearing of labels.
        """
        pass

    def import_labels(self, path: Path) -> LabelUpdateResult:
        with path.open("r", encoding="utf-8", newline=None) as f:
            lines = f.read().splitlines()

        # MVIEW expects lines{1}; an empty file falls into the catch branch.
        header_tokens = _MVIEW_IMPORT_HEADER_RE.findall(lines[0])
        if (
            len(header_tokens) < 2
            or header_tokens[0] != "LABEL"
            or header_tokens[1] != "OFFSET"
        ):
            raise ValueError("unrecognized format")

        imported_labels: list[Label] = []

        for line in lines[1:]:
            match = _MVIEW_IMPORT_ROW_RE.search(line)
            if match is None:
                continue

            name = match.group(1)
            offset_ms_text = match.group(2)
            offset_ms = float(offset_ms_text)
            offset_s = offset_ms / 1000.0

            # MVIEW import sets HOOK = [], i.e. it does not preserve NOTE.
            imported_labels.append(
                Label(name=name, offset_s=offset_s, note="", color="red")
            )

        return LabelUpdateResult(created_labels=imported_labels)
