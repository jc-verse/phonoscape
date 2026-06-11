from typing import TYPE_CHECKING

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
from ..state import ActiveAnalysis


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

    analysis_window_entry = make_entry(f"{config.analysis_window_ms:.1f}")
    lpc_order_entry = make_entry(f"{config.lpc_order:d}")
    fft_eval_points_entry = make_entry(f"{config.fft_eval_points:d}")
    averaging_window_entry = make_entry(f"{config.averaging_window_ms:.1f}")
    overlap_entry = make_entry(f"{config.overlap_ms:.1f}")
    spl_reference_entry = make_entry(f"{config.spl_reference_db:.1f}")
    spectral_cutoff_entry = make_entry(f"{config.spectral_display_cutoff_hz:.1f}")
    pre_emphasis_entry = make_entry(f"{abs(config.pre_emphasis):.2f}")

    add_row(0, "Analysis window (msecs):", analysis_window_entry)
    add_row(1, "Number of LPC coeffs:", lpc_order_entry)
    add_row(2, "# FFT eval points:", fft_eval_points_entry)
    add_row(3, "Averaging window (msecs):", averaging_window_entry)
    add_row(4, "Overlap (msecs):", overlap_entry)
    add_row(5, "SPL reference (dB):", spl_reference_entry)
    add_row(6, "Spectral Display Cutoff (Hz):", spectral_cutoff_entry)

    pre_emphasis_frame = QFrame(main)
    pre_emphasis_layout = QHBoxLayout(pre_emphasis_frame)
    pre_emphasis_layout.setContentsMargins(0, 0, 0, 0)
    pre_emphasis_layout.setSpacing(6)

    adaptive_pre_emphasis_check = QCheckBox("Adaptive", pre_emphasis_frame)
    adaptive_pre_emphasis_check.setChecked(config.pre_emphasis < 0)

    pre_emphasis_layout.addWidget(adaptive_pre_emphasis_check)
    pre_emphasis_layout.addWidget(QLabel("pre-emphasis:", pre_emphasis_frame))
    pre_emphasis_layout.addWidget(pre_emphasis_entry)
    pre_emphasis_layout.addStretch(1)

    main_layout.addWidget(pre_emphasis_frame, 8, 0, 1, 2)

    main_layout.addWidget(
        QLabel("Active Analyses:", main),
        9,
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

    main_layout.addWidget(active_analyses_frame, 9, 1)

    subject_gender_combo = QComboBox(main)
    subject_gender_combo.addItems(["Male", "Female"])
    subject_gender_combo.setCurrentIndex(1 if config.is_female else 0)
    subject_gender_combo.setFixedWidth(120)

    main_layout.addWidget(
        QLabel("Subject Gender:", main),
        10,
        0,
        alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
    )
    main_layout.addWidget(
        subject_gender_combo, 10, 1, alignment=Qt.AlignmentFlag.AlignLeft
    )

    spectrogram_combo = QComboBox(main)
    spectrogram_combo.addItems(["wideband", "mid 1", "mid 2", "narrow"])
    spectrogram_combo.setCurrentIndex(
        max(0, min(3, config.spectrogram_bandwidth_mode - 1))
    )
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

    def on_ok() -> None:
        old_spectral_display_cutoff_hz = config.spectral_display_cutoff_hz
        try:
            config.spectral_display_cutoff_hz = float(spectral_cutoff_entry.text())
            if config.spectral_display_cutoff_hz <= 0:
                config.spectral_display_cutoff_hz = old_spectral_display_cutoff_hz
        except:
            pass

        if config.spectral_display_cutoff_hz != old_spectral_display_cutoff_hz:
            parent.root.freq_domain_view.update_plot(xlim=True)
            parent.root.temporal_view.update_plot(spect_ylim=True)
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
