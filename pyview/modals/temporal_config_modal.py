from typing import Literal, TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from ..menu.view_menu import ViewMenu

from ..state import ScalarTrajDisplay, SpatialTrajDisplay


def open_tempcfg_dialog(parent: ViewMenu) -> None:
    dialog = QDialog(parent.root)
    dialog.setWindowTitle("Configure temporal layout")
    dialog.setModal(True)
    dialog.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

    loaded_names = list(parent.state_model.selected_value.trajectories.keys())
    displayed_specs = list(parent.state_model.temporal_disp_specs)

    outer_layout = QVBoxLayout(dialog)
    outer_layout.setContentsMargins(12, 12, 12, 12)
    outer_layout.setSpacing(0)

    main = QFrame(dialog)
    main_layout = QGridLayout(main)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setHorizontalSpacing(10)
    main_layout.setVerticalSpacing(4)

    outer_layout.addWidget(main)

    main_layout.setColumnStretch(0, 1)
    main_layout.setColumnStretch(1, 0)
    main_layout.setColumnStretch(2, 1)

    main_layout.setRowStretch(0, 0)
    main_layout.setRowStretch(1, 1)
    main_layout.setRowStretch(5, 0)
    main_layout.setRowStretch(6, 0)
    main_layout.setRowStretch(7, 0)

    main_layout.addWidget(QLabel("Loaded", main), 0, 0)
    main_layout.addWidget(QLabel("Displayed", main), 0, 2)

    loaded_list = QListWidget(main)
    displayed_list = QListWidget(main)

    loaded_list.addItems(loaded_names)
    displayed_list.addItems([str(spec) for spec in displayed_specs])

    loaded_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    displayed_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    loaded_list.setMinimumWidth(180)
    displayed_list.setMinimumWidth(180)
    loaded_list.setMinimumHeight(180)
    displayed_list.setMinimumHeight(180)

    main_layout.addWidget(loaded_list, 1, 0)
    main_layout.addWidget(displayed_list, 1, 2)

    middle = QFrame(main)
    middle_layout = QVBoxLayout(middle)
    middle_layout.setContentsMargins(0, 18, 0, 10)
    middle_layout.setSpacing(6)
    middle_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    xfer_button = QPushButton(">", middle)
    delete_button = QPushButton("x", middle)
    up_button = QPushButton("^", middle)
    down_button = QPushButton("v", middle)

    for button in (xfer_button, delete_button, up_button, down_button):
        button.setFixedWidth(28)
        button.setFixedHeight(28)
        middle_layout.addWidget(button)

    main_layout.addWidget(middle, 1, 1, alignment=Qt.AlignmentFlag.AlignTop)

    detail = QFrame(main)
    detail_layout = QHBoxLayout(detail)
    detail_layout.setContentsMargins(0, 4, 0, 0)
    detail_layout.setSpacing(8)

    detail_layout.addWidget(QLabel("Content:", detail))

    content_combo = QComboBox(detail)
    content_combo.setEnabled(False)
    content_combo.setMinimumWidth(180)
    detail_layout.addWidget(content_combo)
    detail_layout.addStretch(1)

    main_layout.addWidget(detail, 5, 0, 1, 3)

    comps = QFrame(main)
    comps_layout = QHBoxLayout(comps)
    comps_layout.setContentsMargins(0, 10, 0, 0)
    comps_layout.setSpacing(8)

    comps_layout.addWidget(QLabel("Components:", comps))

    x_check = QCheckBox("X", comps)
    y_check = QCheckBox("Y", comps)
    comps_layout.addWidget(x_check)
    comps_layout.addWidget(y_check)

    if parent.state_model.dimensions >= 3:
        z_check = QCheckBox("Z", comps)
        comps_layout.addWidget(z_check)
    else:
        z_check = None

    comps_layout.addStretch(1)
    main_layout.addWidget(comps, 6, 0, 1, 3)

    buttons = QFrame(main)
    buttons_layout = QHBoxLayout(buttons)
    buttons_layout.setContentsMargins(0, 16, 0, 0)
    buttons_layout.setSpacing(12)
    buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    ok_button = QPushButton("OK", buttons)
    cancel_button = QPushButton("Cancel", buttons)

    buttons_layout.addWidget(ok_button)
    buttons_layout.addWidget(cancel_button)

    main_layout.addWidget(buttons, 7, 0, 1, 3)

    def selected_displayed_index() -> int | None:
        selected_items = displayed_list.selectedItems()
        if len(selected_items) != 1:
            return None
        return displayed_list.row(selected_items[0])

    def set_component_state(enabled: bool) -> None:
        x_check.setEnabled(enabled)
        y_check.setEnabled(enabled)
        if z_check is not None:
            z_check.setEnabled(enabled)

    def refresh_displayed_listbox() -> None:
        displayed_list.clear()
        displayed_list.addItems([str(spec) for spec in displayed_specs])

    def refresh_button_states() -> None:
        loaded_sel = loaded_list.selectedItems()
        displayed_sel = displayed_list.selectedItems()

        xfer_button.setEnabled(bool(loaded_sel))
        delete_button.setEnabled(bool(displayed_sel))

        if len(displayed_sel) == 1:
            idx = displayed_list.row(displayed_sel[0])
            up_button.setEnabled(idx > 0)
            down_button.setEnabled(idx < len(displayed_specs) - 1)
        else:
            up_button.setEnabled(False)
            down_button.setEnabled(False)

    def refresh_detail_controls() -> None:
        idx = selected_displayed_index()

        if idx is None:
            content_combo.blockSignals(True)
            content_combo.clear()
            content_combo.setEnabled(False)
            content_combo.blockSignals(False)

            x_check.blockSignals(True)
            y_check.blockSignals(True)
            x_check.setChecked(False)
            y_check.setChecked(False)
            x_check.blockSignals(False)
            y_check.blockSignals(False)

            if z_check is not None:
                z_check.blockSignals(True)
                z_check.setChecked(False)
                z_check.blockSignals(False)

            set_component_state(False)
            return

        spec = displayed_specs[idx]

        content_combo.blockSignals(True)
        content_combo.clear()

        if isinstance(spec, ScalarTrajDisplay):
            content_combo.addItems(
                ["SIGNAL", "SPECT", "RMS", "ZC", "F0", "VEL", "ABSVEL"]
            )
            content_combo.setCurrentText(spec.content)
            content_combo.setEnabled(True)
            content_combo.blockSignals(False)

            x_check.blockSignals(True)
            y_check.blockSignals(True)
            x_check.setChecked(False)
            y_check.setChecked(False)
            x_check.blockSignals(False)
            y_check.blockSignals(False)

            if z_check is not None:
                z_check.blockSignals(True)
                z_check.setChecked(False)
                z_check.blockSignals(False)

            set_component_state(False)

        elif isinstance(spec, SpatialTrajDisplay):
            content_combo.addItems(["movement", "velocity", "acceleration"])
            content_combo.setCurrentText(spec.content)
            content_combo.setEnabled(True)
            content_combo.blockSignals(False)

            x_check.blockSignals(True)
            y_check.blockSignals(True)
            x_check.setChecked("x" in spec.components)
            y_check.setChecked("y" in spec.components)
            x_check.blockSignals(False)
            y_check.blockSignals(False)

            if z_check is not None:
                z_check.blockSignals(True)
                z_check.setChecked("z" in spec.components)
                z_check.blockSignals(False)

            set_component_state(True)

        else:
            content_combo.blockSignals(False)
            raise Exception(f"Unknown spec type: {spec}")

    def rewrite_selected_spec() -> None:
        idx = selected_displayed_index()
        if idx is None:
            return

        old = displayed_specs[idx]

        if isinstance(old, ScalarTrajDisplay):
            displayed_specs[idx] = ScalarTrajDisplay(
                traj_name=old.traj_name,
                content=content_combo.currentText(),
            )

        elif isinstance(old, SpatialTrajDisplay):
            components = []
            if x_check.isChecked():
                components.append("x")
            if y_check.isChecked():
                components.append("y")
            if z_check is not None and z_check.isChecked():
                components.append("z")

            # Avoid invalid empty component list.
            if not components:
                components = list(old.components)

            displayed_specs[idx] = SpatialTrajDisplay(
                traj_name=old.traj_name,
                traj_dims=old.traj_dims,
                content=content_combo.currentText(),
                components=components,
            )

        refresh_displayed_listbox()
        displayed_list.setCurrentRow(idx)
        refresh_detail_controls()
        refresh_button_states()

    def on_loaded_select() -> None:
        displayed_list.clearSelection()
        refresh_detail_controls()
        refresh_button_states()

    def on_displayed_select() -> None:
        loaded_list.clearSelection()
        refresh_detail_controls()
        refresh_button_states()

    def on_xfer() -> None:
        selected_rows = sorted(
            loaded_list.row(item) for item in loaded_list.selectedItems()
        )

        for idx in selected_rows:
            traj_name = loaded_list.item(idx).text()
            traj = parent.state_model.selected_value.trajectories[traj_name]

            if traj.kind == "spatial":
                displayed_specs.append(
                    SpatialTrajDisplay(
                        traj_name=traj_name,
                        traj_dims=parent.state_model.dimensions,
                        content="movement",
                        components=["x", "y", "z"][: parent.state_model.dimensions],
                    )
                )
            else:
                displayed_specs.append(
                    ScalarTrajDisplay(traj_name=traj_name, content="SIGNAL")
                )

        refresh_displayed_listbox()
        refresh_button_states()

    def on_delete() -> None:
        indices = sorted(
            (displayed_list.row(item) for item in displayed_list.selectedItems()),
            reverse=True,
        )
        if not indices:
            return

        for idx in indices:
            del displayed_specs[idx]

        refresh_displayed_listbox()
        refresh_detail_controls()
        refresh_button_states()

    def on_move(delta: Literal[1, -1]) -> None:
        idx = selected_displayed_index()
        if idx is None:
            return

        new_idx = idx + delta
        if new_idx < 0 or new_idx >= len(displayed_specs):
            return

        displayed_specs[idx], displayed_specs[new_idx] = (
            displayed_specs[new_idx],
            displayed_specs[idx],
        )

        refresh_displayed_listbox()
        displayed_list.setCurrentRow(new_idx)
        refresh_detail_controls()
        refresh_button_states()

    def on_ok() -> None:
        parent.state_model.temporal_disp_specs = displayed_specs
        parent.root.temporal_view.reset_plot()
        dialog.accept()

    def on_cancel() -> None:
        dialog.reject()

    loaded_list.itemSelectionChanged.connect(on_loaded_select)
    displayed_list.itemSelectionChanged.connect(on_displayed_select)

    xfer_button.clicked.connect(on_xfer)
    delete_button.clicked.connect(on_delete)
    up_button.clicked.connect(lambda: on_move(-1))
    down_button.clicked.connect(lambda: on_move(1))

    content_combo.currentIndexChanged.connect(lambda _idx: rewrite_selected_spec())
    x_check.toggled.connect(lambda _checked: rewrite_selected_spec())
    y_check.toggled.connect(lambda _checked: rewrite_selected_spec())
    if z_check is not None:
        z_check.toggled.connect(lambda _checked: rewrite_selected_spec())

    ok_button.clicked.connect(on_ok)
    cancel_button.clicked.connect(on_cancel)

    ok_button.setDefault(True)
    ok_button.setAutoDefault(True)
    cancel_button.setAutoDefault(False)

    refresh_detail_controls()
    refresh_button_states()

    dialog.resize(520, 420)

    root_geometry = parent.root.frameGeometry()
    dialog_geometry = dialog.frameGeometry()
    dialog_geometry.moveCenter(root_geometry.center())
    dialog.move(dialog_geometry.topLeft())

    dialog.exec()
