from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

if TYPE_CHECKING:
    from .menu_bar import MenuBar
from ..data.process import get_local_measures
from ..state import SpatialTrajDisplay, ScalarTrajDisplay


class DataMenu(QMenu):
    def __init__(self, parent: MenuBar):
        super().__init__("Data", parent)

        self.state_model = parent.state_model
        self.root = parent.root

        self.addAction("Report", self._report)
        self.addAction("Track formants", parent._todo("Track formants"))
        self.addAction("Spectral analysis...", parent._todo("Spectral analysis"))

    def _report(self):
        print(
            f"\n{self.state_model.selected_value.name}:  cursor @ {self.state_model.cursor_s * 1000:.1f} ms; selection is [{self.state_model.head_s * 1000:.1f} {self.state_model.tail_s * 1000:.1f}] ({self.state_model.tail_s * 1000 - self.state_model.head_s * 1000:.1f}) ms"
        )
        if self.state_model.config.audio_traj:
            traj = self.state_model.selected_value.trajectories[
                self.state_model.config.audio_traj
            ]
            # TODO: configurable window size
            audio_measures = get_local_measures(
                traj, self.state_model.cursor_s, window_ms=20
            )
            print(
                f"Window {20:.1f} ms:  {audio_measures.zero_crossings} zero crossings, RMS = {audio_measures.rms:.2f} ({audio_measures.rms_db:.2f} dB), F0 = {audio_measures.f0_hz:.2f} Hz, L1 = {audio_measures.L1:.2f}, skew = {audio_measures.skew:.2f}, kurt = {audio_measures.kurt:.2f}"
            )
            print("Formants (BW):", end="")
            nf = len(audio_measures.formants)
            for fi in range(nf):
                formant, bw = audio_measures.formants[fi]
                print(f"  F{fi + 1:d} = {formant:.0f} ({bw:.0f})", end="")
                print()
        traj_measures: list[tuple[str, float]] = []
        for spec, (_, data) in zip(
            self.root.temporal_view._get_temp_disp_specs(),
            self.root.temporal_view.plotting_data,
        ):
            if spec.traj_name == self.state_model.config.audio_traj:
                continue
            traj = self.state_model.selected_value.trajectories[spec.traj_name]
            idx = round(self.state_model.cursor_s * traj.sample_rate_hz)
            if isinstance(spec, ScalarTrajDisplay):
                if spec.content in {"SIGNAL", "RMS", "ZC", "VEL", "ABSVEL"}:
                    traj_measures.append((str(spec), data[idx]))
                elif spec.content == "SPECT":
                    continue
            else:
                if (
                    spec.content in {"velocity", "acceleration"}
                    and len(spec.components) == spec.traj_dims
                ):
                    traj_measures.append((str(spec), data[idx, 0]))
                else:
                    for comp, val in zip(spec.components, data[idx]):
                        prefix = {"movement": "", "velocity": "v", "acceleration": "a"}[
                            spec.content
                        ]
                        traj_measures.append((f"{prefix}{spec.traj_name}{comp}", val))

        print("\nTraj: ", end="")
        for name, _ in traj_measures:
            print(f" {name:>6s}", end="")
        print("\nVals: ", end="")
        for _, value in traj_measures:
            print(f" {value:6.1f}", end="")
        print()
