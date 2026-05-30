from . import pyview

if __name__ == "__main__":
    import argparse

    # [ ] CONFIG
    # [ ] DPROC
    # [x] FTRAJ
    # [ ] HEAD
    # [ ] LABELS
    # [ ] LPROC
    # [ ] IS3D
    # [x] MAP / TEMPMAP
    # [x] PALATE
    # [ ] PHARYNX
    # [ ] PPROC
    # [ ] SEX
    # [x] SPLINE
    # [ ] SPREAD
    # [ ] TAIL
    # [ ] SPATEX
    # [ ] VIEW
    # [ ] NAME
    # [ ] VLIST
    # [ ] VLSEL
    # [ ] SPECLIM

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
        "--palate", type=str, help="Variable name for palate trace (optional)."
    )
    parser.add_argument(
        "--spline",
        type=str,
        nargs="+",
        help="List of trajectory names to apply spline interpolation (default: all trajectories starting with 'T').",
    )
    parser.add_argument(
        "--audio",
        type=str,
        help="Variable name for audio trajectory - for spectrogram plotting (default: first scalar trajectory with sampling rate > 1000 Hz).",
    )
    parser.add_argument(
        "--framing",
        type=str,
        help="Variable name for framing trajectory (default: --audio, or first trajectory if no audio found).",
    )
    parser.add_argument(
        "--temporal-disp-trajs",
        type=str,
        nargs="+",
        help="List of variable names to include in temporal display (default: all plus {--audio}_SPECT).",
    )
    args = parser.parse_args()

    pyview(
        args.file,
        args.variables,
        palate=args.palate,
        spline=args.spline,
        audio=args.audio,
        framing=args.framing,
        temporal_disp_trajs=args.temporal_disp_trajs,
    )
