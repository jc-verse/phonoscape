from typing import TYPE_CHECKING, overload

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from ..menu.data_menu import DataMenu
from ..data.process import analyze_audio
from ..state import ActiveAnalysis, SpectrogramBandwidth


def open_spectral_analysis_dialog(parent: DataMenu) -> None:
    dialog = QDialog(parent.root)
    dialog.setWindowTitle("Configure spectral analysis")
    dialog.setModal(True)
    dialog.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

    outer_layout = QVBoxLayout(dialog)
    outer_layout.setContentsMargins(12, 12, 12, 12)
    outer_layout.setSpacing(14)

    main = QFrame(dialog)
    main_layout = QGridLayout(main)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setHorizontalSpacing(6)
    main_layout.setVerticalSpacing(6)

    config = parent.state.app_config

    def make_entry(text: str, width: int = 80) -> QLineEdit:
        entry = QLineEdit(text, main)
        entry.setFixedWidth(width)
        return entry

    def add_row(row: int, label: str, widget: QLineEdit) -> None:
        main_layout.addWidget(
            QLabel(label, main),
            row,
            0,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        main_layout.addWidget(widget, row, 1, alignment=Qt.AlignmentFlag.AlignLeft)

    main_layout.addWidget(
        QLabel("Active analyses:", main),
        0,
        0,
        alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
    )

    active_analyses_frame = QFrame(main)
    active_analyses_layout = QGridLayout(active_analyses_frame)
    active_analyses_layout.setContentsMargins(0, 0, 0, 0)
    active_analyses_layout.setHorizontalSpacing(8)
    active_analyses_layout.setVerticalSpacing(0)

    lpc_check = QCheckBox("LPC", active_analyses_frame)
    dft_check = QCheckBox("DFT", active_analyses_frame)
    averaged_dft_check = QCheckBox("AVG", active_analyses_frame)
    cepstral_smoothing_check = QCheckBox("CEPS", active_analyses_frame)

    lpc_check.setChecked(bool(config.active_analyses & ActiveAnalysis.LPC))
    dft_check.setChecked(bool(config.active_analyses & ActiveAnalysis.DFT))
    averaged_dft_check.setChecked(bool(config.active_analyses & ActiveAnalysis.AVG))
    cepstral_smoothing_check.setChecked(
        bool(config.active_analyses & ActiveAnalysis.CEPS)
    )

    active_analyses_layout.addWidget(lpc_check, 0, 0)
    active_analyses_layout.addWidget(dft_check, 0, 1)
    active_analyses_layout.addWidget(averaged_dft_check, 1, 0)
    active_analyses_layout.addWidget(cepstral_smoothing_check, 1, 1)

    main_layout.addWidget(active_analyses_frame, 0, 1)

    analysis_window_entry = make_entry(f"{config.analysis_window_ms:.1f}")
    lpc_order_entry = make_entry(f"{config.lpc_order:d}")
    fft_eval_points_entry = make_entry(f"{config.fft_eval_points:d}")
    averaging_window_entry = make_entry(f"{config.averaging_window_ms:.1f}")
    overlap_entry = make_entry(f"{config.overlap_ms:.1f}")
    spl_reference_entry = make_entry(f"{config.spl_reference_db:.1f}")
    spectral_cutoff_entry = make_entry(f"{config.spectral_display_cutoff_hz:.1f}")
    pre_emphasis_entry = make_entry(
        f"{config.pre_emphasis:.2f}" if config.pre_emphasis is not None else ""
    )

    add_row(1, "Analysis window (ms):", analysis_window_entry)
    add_row(2, "Number of LPC coeffs:", lpc_order_entry)
    add_row(3, "# FFT eval points:", fft_eval_points_entry)
    add_row(4, "Averaging window (ms):", averaging_window_entry)
    add_row(5, "Overlap (ms):", overlap_entry)
    add_row(6, "SPL reference (dB):", spl_reference_entry)
    add_row(7, "Spectral display cutoff (Hz):", spectral_cutoff_entry)

    pre_emphasis_frame = QFrame(main)
    pre_emphasis_layout = QHBoxLayout(pre_emphasis_frame)
    pre_emphasis_layout.setContentsMargins(0, 0, 0, 0)
    pre_emphasis_layout.setSpacing(6)

    adaptive_pre_emphasis_check = QCheckBox("(Adaptive)", pre_emphasis_frame)
    adaptive_pre_emphasis_check.setChecked(config.pre_emphasis is None)
    adaptive_pre_emphasis_check.toggled.connect(
        lambda checked: pre_emphasis_entry.setEnabled(not checked)
    )

    pre_emphasis_layout.addWidget(adaptive_pre_emphasis_check)
    pre_emphasis_layout.addWidget(QLabel("Pre-emphasis:", pre_emphasis_frame))
    pre_emphasis_layout.addWidget(pre_emphasis_entry)
    pre_emphasis_layout.addStretch(1)

    main_layout.addWidget(pre_emphasis_frame, 8, 0, 1, 2)

    subject_gender_combo = QComboBox(main)
    subject_gender_combo.addItems(["Male", "Female"])
    subject_gender_combo.setCurrentIndex(1 if config.is_female else 0)
    subject_gender_combo.setFixedWidth(120)

    main_layout.addWidget(
        QLabel("Subject gender:", main),
        10,
        0,
        alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
    )
    main_layout.addWidget(
        subject_gender_combo, 10, 1, alignment=Qt.AlignmentFlag.AlignLeft
    )

    spectrogram_combo = QComboBox(main)
    spectrogram_combo.addItems(["wideband", "mid 1", "mid 2", "narrow"])
    spectrogram_combo.setCurrentIndex(config.spectrogram_bandwidth_mode.value - 1)
    spectrogram_combo.setFixedWidth(120)

    main_layout.addWidget(
        QLabel("Spectrogram:", main),
        11,
        0,
        alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
    )
    main_layout.addWidget(
        spectrogram_combo, 11, 1, alignment=Qt.AlignmentFlag.AlignLeft
    )

    outer_layout.addWidget(main)

    buttons = QFrame(dialog)
    buttons_layout = QHBoxLayout(buttons)
    buttons_layout.setContentsMargins(0, 0, 0, 0)
    buttons_layout.setSpacing(6)
    buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    @overload
    def parse_num(
        field: QLineEdit, name: str, type: type[int], limit: int = 0
    ) -> int | None: ...
    @overload
    def parse_num(
        field: QLineEdit, name: str, type: type[float], limit: float = 0.0
    ) -> float | None: ...
    def parse_num(
        field: QLineEdit, name: str, type, limit: int | float = 0
    ) -> int | float | None:
        try:
            value = type(field.text())
        except ValueError:
            return None
        if value <= limit or value == getattr(config, name):
            return None
        return value

    def on_ok() -> None:
        update_temporal_view = False
        update_spectrum_ylim = False
        active_analyses = ActiveAnalysis(0)
        if lpc_check.isChecked():
            active_analyses |= ActiveAnalysis.LPC
        if dft_check.isChecked():
            active_analyses |= ActiveAnalysis.DFT
        if averaged_dft_check.isChecked():
            active_analyses |= ActiveAnalysis.AVG
        if cepstral_smoothing_check.isChecked():
            active_analyses |= ActiveAnalysis.CEPS
        config.active_analyses = active_analyses
        if analysis_window_ms := parse_num(
            analysis_window_entry, "analysis_window_ms", float
        ):
            update_temporal_view = (
                update_temporal_view or analysis_window_ms != config.analysis_window_ms
            )
            config.analysis_window_ms = analysis_window_ms
            if update_temporal_view:
                parent.root.zoomed_audio_view.update_plot(xlim=True)
        if lpc_order := parse_num(lpc_order_entry, "lpc_order", int):
            config.lpc_order = lpc_order
        if fft_eval_points := parse_num(fft_eval_points_entry, "fft_eval_points", int):
            update_temporal_view = (
                update_temporal_view or fft_eval_points != config.fft_eval_points
            )
            config.fft_eval_points = fft_eval_points
        if averaging_window_ms := parse_num(
            averaging_window_entry, "averaging_window_ms", float
        ):
            update_temporal_view = (
                update_temporal_view
                or averaging_window_ms != config.averaging_window_ms
            )
            config.averaging_window_ms = averaging_window_ms
        if overlap_ms := parse_num(overlap_entry, "overlap_ms", float):
            update_temporal_view = (
                update_temporal_view or overlap_ms != config.overlap_ms
            )
            config.overlap_ms = overlap_ms
        if spl_reference_db := parse_num(
            spl_reference_entry, "spl_reference_db", float, -float("inf")
        ):
            update_spectrum_ylim = config.spl_reference_db != spl_reference_db
            config.spl_reference_db = spl_reference_db
        if spectral_display_cutoff_hz := parse_num(
            spectral_cutoff_entry, "spectral_display_cutoff_hz", float
        ):
            config.spectral_display_cutoff_hz = spectral_display_cutoff_hz
            parent.root.cursor_spect_view.update_plot(xlim=True)
            parent.root.temporal_view.update_plot(spect_ylim=True)
        if adaptive_pre_emphasis_check.isChecked():
            config.pre_emphasis = None
        elif pre_emphasis := parse_num(pre_emphasis_entry, "pre_emphasis", float):
            if pre_emphasis <= 1:
                config.pre_emphasis = pre_emphasis
        subject_gender = subject_gender_combo.currentText()
        is_female = subject_gender == "Female"
        update_temporal_view = update_temporal_view or is_female != config.is_female
        config.is_female = is_female
        spectrogram_bandwidth_mode = spectrogram_combo.currentIndex() + 1
        if spectrogram_bandwidth_mode != config.spectrogram_bandwidth_mode.value:
            config.spectrogram_bandwidth_mode = SpectrogramBandwidth(
                spectrogram_bandwidth_mode
            )
            update_temporal_view = True
        if update_temporal_view:
            if parent.state.app_config.audio_traj:
                # Invalidate all previous computations
                for v in parent.state.app_config.data.values():
                    v.audio_traj = None
                parent.state.selected_value.audio_traj = analyze_audio(
                    parent.state.selected_value.trajectories[
                        parent.state.app_config.audio_traj
                    ],
                    parent.state.app_config,
                )
            parent.root.temporal_view.update_plot(trajectories=True)
        parent.root.cursor_spect_view.update_plot(data=True, ylim=update_spectrum_ylim)
        dialog.accept()

    def on_cancel() -> None:
        dialog.reject()

    ok_button = QPushButton("OK", buttons, autoDefault=True, default=True)
    ok_button.clicked.connect(on_ok)
    buttons_layout.addWidget(ok_button)

    cancel_button = QPushButton("Cancel", buttons, autoDefault=False)
    cancel_button.clicked.connect(on_cancel)
    buttons_layout.addWidget(cancel_button)

    outer_layout.addWidget(buttons)

    dialog.adjustSize()
    dialog.setFixedSize(dialog.sizeHint())

    root_geometry = parent.root.frameGeometry()
    dialog_geometry = dialog.frameGeometry()
    dialog_geometry.moveCenter(root_geometry.center())
    dialog.move(dialog_geometry.topLeft())

    dialog.exec()
