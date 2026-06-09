from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

if TYPE_CHECKING:
    from .menu_bar import MenuBar
from ..state import ScalarTrajDisplay
from ..data.process import get_cog


class DataMenu(QMenu):
    def __init__(self, parent: MenuBar):
        super().__init__("Data", parent)

        self.state = parent.state
        self.root = parent.root

        self.addAction("Report", self._report)
        self.addAction("Track formants", parent._todo("Track formants"))
        self.addAction("Spectral analysis...", parent._todo("Spectral analysis"))

    def _report(self):
        print(
            f"\n{self.state.selected_value.name}:  cursor @ {self.state.cursor_s * 1000:.1f} ms; selection is [{self.state.head_s * 1000:.1f} {self.state.tail_s * 1000:.1f}] ({self.state.tail_s * 1000 - self.state.head_s * 1000:.1f}) ms"
        )
        if traj := self.state.selected_value.audio_traj:
            idx = round(self.state.cursor_s * traj.sample_rate_hz)
            cog = get_cog(traj, self.state.cursor_s)
            print(
                f"Window {20:.1f} ms:  {traj.zc[idx]} zero crossings, RMS = {traj.rms[idx]:.2f} ({traj.rms_db[idx]:.2f} dB), F0 = {traj.f0.raw_hz[idx]:.2f} Hz, L1 = {cog.l1:.2f}, skew = {cog.skew:.2f}, kurt = {cog.kurt:.2f}"
            )
            print("Formants (BW):", end="")
            nf = len(traj.formants)
            for fi in range(nf):
                formant, bw = traj.formants[fi]
                print(f"  F{fi + 1:d} = {formant[idx]:.0f} ({bw[idx]:.0f})", end="")
                print()
        traj_measures: list[tuple[str, float]] = []
        for spec, (_, data) in zip(
            self.root.temporal_view._get_temp_disp_specs(),
            self.root.temporal_view.plotting_data,
        ):
            if spec.traj_name == self.state.app_config.audio_traj:
                continue
            traj = self.state.selected_value.trajectories[spec.traj_name]
            idx = round(self.state.cursor_s * traj.sample_rate_hz)
            if isinstance(spec, ScalarTrajDisplay):
                if spec.content in {"SIGNAL", "RMS", "ZC", "F0", "VEL", "ABSVEL"}:
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
