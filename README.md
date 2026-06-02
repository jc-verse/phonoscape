# PyView

Python port of MView

```bash
uv sync
source .venv/bin/activate
```

```bash
python -m pyview ./test_data/S02_data.mat --palate S02_pal --temporal-disp-trajs AUDIO_SPECT TDx vTDx TDz vTDz
```

## Command-line arguments

You can run `python -m pyview --help` to see the full list of command-line arguments.

- First, you need to provide a `file` argument pointing to a `.mat` [dataset file](#dataset-format).
- Then, you can optionally provide a `variables` pattern. It uses [`fnmatch`](https://docs.python.org/3/library/fnmatch.html), so you can use `*` to match a sequence of characters and `?` to match a single character. If no variable pattern is provided, then all variables in the dataset file are used.
- Finally, you can provide any number of options:
  - `--palate VAR` (MVIEW `PALATE`): use the variable `VAR` (in the `file`) to plot a palate curve in the spatial view. If specified, the variable must contain a `[n_samples × n_dims]` array of palate points. If unspecified, no palate is plotted.
  - `--spline TRAJ1 TRAJ2 ...` (MVIEW `SPLINE`): specifies that the trajectories `TRAJ1`, `TRAJ2`, etc. (in each variable) should have a spline fitted in the spatial view. If specified, all names must refer to spatial trajectories. If unspecified, then all spatial trajectories with name starting with `T` are used as default.
  - `--audio TRAJ`: specifies that the trajectory `TRAJ` (in each variable) contains audio data. If specified, the name must refer to a scalar trajectory. If unspecified, then the first scalar trajectory with a sampling rate `> 1000` is used as the default. If no such trajectory exists, then all audio-related features (spectrogram time-slice, playback, etc.) are disabled.
  - `--framing TRAJ` (MVIEW `FTRAJ`): specifies that the trajectory `TRAJ` (in each variable) should be used for temporal framing. If specified, the name must refer to a scalar trajectory. If unspecified, then the audio trajectory is used as the default framing trajectory, and if no audio trajectory is found, then the first trajectory of any kind is used as the framing trajectory.
  - `--temporal-disp-trajs SPEC1 SPEC2 ...` (MVIEW `TEMPMAP`): a list of temporal view specifications. Each specification specifies one temporal plot.
    - If designating a scalar trajectory: `TRAJ` or `TRAJ_MODIFIER`, where `MODIFIER` can be: `SPECT` (spectrogram), `RMS` (root mean square), `ZC` (zero-crossing rate), `VEL` (velocity), `ABSVEL` (absolute velocity).
    - If designating a spatial trajectory: `TRAJ`, optionally prefixed by `v` or `a`, and optionally suffixed by a subset of `xyz`, indicating if the trajectory should be movement, velocity, or acceleration, and which dimensions to plot. Specifying `xyz` is equivalent to no specification. Note that following MVIEW behavior, the velocity/acceleration of the whole vector (e.g., `vTD`) only displays the magnitude (and is therefore unsigned), while the velocity/acceleration of specific dimensions (e.g., `vTDx`, `vTDxy`) displays each separate dimension (and is signed).

    These specification names can also be obtained from the "Configure temporal view" dialog.
  - `--comps COMP1 COMP2 ...` (MVIEW `IS3D`): equivalent to the dataset `NCOMPS` [field](#dataset-format), but used as a global fallback when the `NCOMPS` field is absent. This global configuration is also used for non-trajectory data, such as palate trace. A single number `N` is equivalent to `0 .. N-1`.

## Dataset format

The `.mat` file contains three levels:

- Variables: each PyView window views one variable.
- Trajectories: each variable contains one or more trajectories, represented as an array of structs.
- Fields: each trajectory struct has required and optional fields.

Only variables that contain structs are considered valid variables. Other variables (those that contain plain arrays) are considered supplementary data. They are only useful if some other [argument](./arguments.md) refers to them:

- `--palate`: looks for a variable containing a `[n_samples × n_dims]` array of palate points.

The following fields are required for each trajectory struct:

- `NAME` (string): trajectory name. Will be uppercased and stripped of underscores. The actual names absolutely do not matter with one quirk: if the `--spline` [argument](#command-line-arguments) is not provided, all spatial trajectories with name starting with `T` will be used as default.
- `SRATE` (float): sampling rate in Hz. The actual sampling rate value only matters in one place: if the `--audio` [argument](#command-line-arguments) is not provided, then the first scalar trajectory with a sampling rate `> 1000` is used as the default audio trajectory.
- `SIGNAL` (array `[n_samples × n_dims]`): 1D is scalar, 2D or 3D is spatial. Higher dimensions are truncated off and moved into `ANGLES`; if `ANGLES` is also provided, then the extra dimensions are ignored and `ANGLES` is used instead. Currently only 3D is well-supported for spatial trajectories.

All trajectories in a variable are expected to have roughly the same `n_samples * SRATE`. When displaying, the minimum duration is used (i.e., where all trajectories have data).

The following optional fields are effectively variable-wide metadata. Only the first struct's field is used.

- `LABELS` (data type TODO): TODO. The `--labels` [argument](#command-line-arguments) takes priority over this. Only the first struct's `LABELS` field is used.
- `CONTOURS` (data type TODO): TODO.

The following optional fields may be provided for each trajectory struct:

- `COLOR` (array `[1 × 3]`, each in range `[0, 1]`): Specifies the RGB color. Scalar trajectories become text-color and spatial trajectories get an arbitrary color.
- `SPREAD` (array `[1 × 2]`): TODO.
- `NCOMPS` (number or array `[1 × n_dims]`):
  - If a number, must be either 2 or 3. If 3, then the trajectory data must have at least 3 dimensions, and the first 3 are used as XYZ coordinates for the spatial view. This is practically useless, though, because it can be inferred. So the only useful case is if `NCOMPS` is 2 but the trajectory data has 3 dimensions. In that case, only the first 2 dimensions are used for the spatial view, and the 3rd dimension is treated as `ANGLES`.
  - If an array, specifies the column indices of the trajectory data for each dimension. For example, if the trajectory has 3 dimensions but `NCOMPS` is `[0, 2]`, then the 1st and 3rd dimensions (which are normally `x` and `z`) are used for the spatial view, and the 2nd dimension is treated as `ANGLES`. You may also use it to reorder dimensions, e.g., `[0, 2, 1]` uses the data's `z`-axis as the spatial `y`-axis and the data's `y`-axis as the spatial `z`-axis. It must contain no duplicates and all indices must be valid for the trajectory data dimensions.
  - If not provided, then it's inferred from `SIGNAL.shape[1]`, with the first 3 dimensions used for the spatial view (in `x`, `y`, `z` order) and any extra dimensions treated as `ANGLES`.
- `ANGLES` (array `[n_samples × n_extra]`): Only used by external data procedures.
