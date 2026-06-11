from typing import cast
from . import pyview

if __name__ == "__main__":
    import argparse

    # [ ] CONFIG
    # [ ] DPROC
    # [x] FTRAJ
    # [x] HEAD
    # [ ] LABELS
    # [ ] LPROC
    # [x] IS3D
    # [x] MAP / TEMPMAP
    # [x] PALATE
    # [x] PHARYNX
    # [ ] PPROC
    # [x] SEX
    # [x] SPLINE
    # [ ] SPREAD
    # [x] TAIL
    # [x] SPATEX
    # [x] VIEW
    # [x] NAME
    # [x] VLIST
    # [x] VLSEL
    # [x] SPECLIM

    parser = argparse.ArgumentParser(
        description="PyView: A tool for visualizing .mat files."
    )
    parser.add_argument("file", type=str, help="Path to the .mat file to visualize.")
    parser.add_argument(
        "variables",
        type=str,
        nargs="?",
        default="*",
        help="Glob pattern to filter variables (default: '*').",
    )
    parser.add_argument(
        "--palate", type=str, 
        metavar="VAR", help="Variable name for palate trace (optional)."
    )
    parser.add_argument(
        "--pharynx", type=str, 
        metavar="VAR", help="Variable name for pharynx trace (optional)."
    )
    parser.add_argument(
        "--spline",
        type=str,
        nargs="+",
        metavar="TRAJ",
        help="List of trajectory names to apply spline interpolation (default: all spatial trajectories starting with 'T').",
    )
    parser.add_argument(
        "--audio",
        type=str,
        metavar="TRAJ",
        help="Variable name for audio trajectory - for spectrogram plotting and playback (default: first scalar trajectory with sampling rate > 1000 Hz).",
    )
    parser.add_argument(
        "--framing",
        type=str,
        metavar="TRAJ",
        help="Variable name for framing trajectory (default: --audio, or first trajectory if no audio found).",
    )
    parser.add_argument(
        "--temporal-display",
        type=str,
        metavar="SPEC",
        nargs="+",
        help="List of variable names to include in temporal display (default: all plus {--audio}_SPECT).",
    )
    parser.add_argument(
        "--spatial-exclude",
        type=str,
        nargs="+",
        metavar="TRAJ",
        help="List of trajectory names to exclude from the spatial view (default: none).",
    )
    parser.add_argument(
        "--comps",
        type=int,
        nargs="+",
        metavar=("N|COL", "COL"),
        help="Number of dimensions for spatial trajectories, or list of column indices to use for each dimension (default: all dimensions, up to 3, are used for spatial view in x,y,z order).",
    )
    parser.add_argument(
        "--view",
        type=float,
        nargs=3,
        metavar=("ELEV", "AZIM", "ROLL"),
        help="Initial view angles (degrees) for the 3D spatial display: azimuth, elevation and roll. Only has an effect when the data is 3D. Only has an effect on the first opened window; subsequent windows inherit the opening window's view (default: 0, -90, 0).",
    )
    parser.add_argument(
        "--head",
        type=float,
        metavar="MS",
        help="Start of selection (ms) for the temporal view (default: 0).",
    )
    parser.add_argument(
        "--tail",
        type=float,
        metavar="MS",
        help="End of selection (ms) for the temporal view (default: duration of the current trajectory).",
    )
    parser.add_argument(
        "--sex",
        choices=["M", "F"],
        help="Pass 'F' for female, 'M' for male. This can be later customized in the 'Configure spectral analysis' dialog, but it affects the default LPC degree (default: M).",
    )
    parser.add_argument(
        "--spect-lim",
        type=float,
        metavar="HZ",
        help="Frequency upper limit (Hz) for spectrogram display (default: Nyquist frequency).",
    )
    args = parser.parse_args()

    pyview(
        args.file,
        args.variables,
        palate=args.palate,
        pharynx=args.pharynx,
        spline=args.spline,
        audio=args.audio,
        framing=args.framing,
        temporal_display=args.temporal_display,
        spatial_exclude=args.spatial_exclude,
        comps=(
            None
            if not args.comps
            else args.comps[0] if len(args.comps) == 1 else args.comps
        ),
        view=cast(tuple[float, float, float], tuple(args.view)) if args.view else None,
        head=args.head,
        tail=args.tail,
        sex=args.sex,
        spect_lim=args.spect_lim,
    )
