# PyView

Python port of MView

```bash
uv sync
source .venv/bin/activate
```

```bash
python -m pyview ./test_data/S02_data.mat --palate S02_pal --temporal-disp-trajs AUDIO_SPECT TDx vTDx TDz vTDz
```

## Central concepts

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
    - If designating a scalar trajectory: `TRAJ` or `TRAJ_MODIFIER`, where `MODIFIER` can be: `SPECT` (spectrogram), `RMS` (root mean square), `ZC` (zero-crossing rate), `F0` (fundamental frequency), `VEL` (velocity), `ABSVEL` (absolute velocity).
    - If designating a spatial trajectory: `TRAJ`, optionally prefixed by `v` or `a`, and optionally suffixed by a subset of `xyz`, indicating if the trajectory should be movement, velocity, or acceleration, and which dimensions to plot. Specifying `xyz` is equivalent to no specification. Note that following MVIEW behavior, the velocity/acceleration of the whole vector (e.g., `vTD`) only displays the magnitude (and is therefore unsigned), while the velocity/acceleration of specific dimensions (e.g., `vTDx`, `vTDxy`) displays each separate dimension (and is signed).

    These specification names can also be obtained from the "Temporal layout" dialog.

  - `--comps COMP1 COMP2 ...` (MVIEW `IS3D`): equivalent to the dataset `NCOMPS` [field](#dataset-format), but used as a global fallback when the `NCOMPS` field is absent. This global configuration is also used for non-trajectory data, such as palate trace. A single number `N` is equivalent to `0 .. N-1`.
  - `--head MS` (MVIEW `HEAD`): the position (in milliseconds) of the left edge of the temporal selection. If specified, it must be a non-negative number less than `--tail - 25`. If unspecified, it defaults to the start of the data (0 ms).
  - `--tail MS` (MVIEW `TAIL`): the position (in milliseconds) of the right edge of the temporal selection. If specified, it must be a non-negative number greater than `--head + 25`. If unspecified, it defaults to the end of the first variable's data.

Note that the framing and audio trajectory discovery is slightly different from MVIEW's; for one, we never special-case the very first trajectory.

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

For 3D data, the following axis-component mapping is preferred (configurable via the `--comps` [argument](#command-line-arguments)):

- x-axis is sagittal (posterior = negative, anterior = positive)
- y-axis is transverse (right = negative, left = positive)
- z-axis is longitudinal (inferior = negative, superior = positive).

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

## Menu bar

### File menu

- **Variables**: Only available when viewing >1 variables. Each variable opens in a new window. The first variable is selected by default. We ensure that the same variable can only be opened in one window at a time. Opening a new window inherits most of the current configuration, _except_ the cursor position which is always reset to the beginning.
  - **Previous (Ctrl+1)**: Opens the previous variable in the order they appear in the dataset. Cycles across the boundary (slightly different from MVIEW).
  - **Next (Ctrl+2)**: Opens the next variable in the order they appear in the dataset. Cycles across the boundary (slightly different from MVIEW).
  - **Next; close current (Ctrl+3)**: As it says.
  - **Next plus export (Ctrl+4)**: TODO
  - **Next; export, close current (Ctrl+5)**: TODO
  - **Next; save labels, close current (Ctrl+6)**: TODO
  - **Next; export/save labels, close current (Ctrl+7)**: TODO
- **Save**: TODO
- **Export**: TODO
- **Open figure**: Opens one of the figures in a new window with matplotlib tools (configuring dimensions, save as file, etc.), like what you get with `plt.show()`; usually for the purpose of exporting the figure, but also useful for detailed inspection. This is equivalent to MVIEW's "Duplicate window".
  - **Temporal view**: Open the right panel only.
  - **Spatial view**: Open the top-left panel only.
  - **Entire window**: TODO
- **Close window**: Closes the current window only.
- **Close all**: Closes all variable windows, which should quit the application.

### Data menu

- **Report**: Prints data at the cursor location to the terminal. Format:

  ```plain
  {Variable name}:  cursor @ {cursor} ms; selection is [{head} {tail}] ({duration}) ms
  Window {length} ms:  {x} zero crossings, RMS = {x} ({x} dB), F0 = {x} Hz, L1 = {x}, skew = {x}, kurt = {x}
  Formants (BW):  F1 = {loc} ({bw})  F2 = {loc} ({bw})  ...
  Traj:     TDx    TDy ...
  Vals:   -59.3   -7.6 ...
  ```

  Note that the "Traj" list outputs at least one column for each temporally displayed trajectory (except spectrograms), depending on which dimensions are being viewed.

- **Track formants**: TODO
- **Spectral analysis**: TODO

### View menu

- **Temporal layout**: Configure which trajectories to display in the temporal view. It launches a dialog where you can:
  - Select available trajectories from the left-hand side to add (`>`) to the display area on the right-hand side.
  - Select displayed trajectories from the right-hand side to remove (`x`) from the display area.
  - Select one displayed trajectory from the right-hand side to reorder (`^` and `v`).
  - Select one displayed trajectory from the right-hand side to customize its content. For spatial trajectories, you can choose to display position, velocity, or acceleration, and which dimensions to display. For scalar trajectories, you can choose to apply a temporal analysis (spectrogram, RMS, zero-crossing rate, fundamental frequency, etc.).

  The list of names on the right-hand side are known as "temporal display specifications". They are also used in the `--temporal-disp-trajs` [argument](#command-line-arguments) and the "Report" output.

- **Set common scaling**: Opens a dialog. TODO
- **Spatial options**: Configure the spatial display.
  - **Hide spline**: Only available when the `--spline` [argument](#command-line-arguments) (including its default value) specifies a non-empty set. Toggles the display of the spline curve.
  - **Free rotate**: Only available when the display is 3-dimensional. Toggles whether the spatial view can be freely rotated by dragging with the mouse.
  - **2D/3D view (1/2/3)**: Only available when the display is 3-dimensional. 6 predefined camera positions. These options are visually consistent with MVIEW, but MATLAB uses different specification conventions from matplotlib, so the physical parameters are different.

    | Name        | Elevation | Azimuth | Roll | Behavior                          |
    | ----------- | --------- | ------- | ---- | --------------------------------- |
    | 2D view (1) | 90        | 0       | 90   | Transverse section, superior view |
    | 2D view (2) | 0         | -90     | 0    | Sagittal section, right view      |
    | 2D view (3) | 0         | -180    | 0    | Coronal section, anterior view    |
    | 3D view (1) | 18        | 20      | 0    | Left anterosuperior view          |
    | 3D view (2) | -30       | -62.5   | 0    | Left posteroinferior view         |
    | 3D view (3) | -20       | -117    | 0    | Left anteroinferior view          |

  - **Specify view**: Opens a dialog to configure your own elevation/azimuth/roll parameters.

### Play menu

Only available if an audio trajectory exists.

- **Play (Ctrl+P)**: Play the audio at the specified interval:
  - **Selection**: Between head and tail.
  - **Entire file**: From the start to the end of the data.
  - **To cursor**: Between head and the cursor. If cursor is before head, then play selection.
  - **From cursor**: Between cursor and tail. If cursor is after tail, then play selection.
  - **150ms @ cursor**: 150ms centered at the cursor, clamped to the selection (different from MVIEW; if you want the MVIEW behavior, slightly expand your selection).

Note that the behavior configured here applies to the "Play" button in the navbar as well.

### Selection menu

Currently a minimum of 25ms is enforced for the selection duration. Customization will be allowed.

- **Set head to cursor**: As it says; clamped to `tail - 25ms`.
- **Set tail to cursor**: As it says; clamped to `head + 25ms`.
- **Set selection to label pair**: Only has an effect if the cursor is between two labels. Sets head to the previous label and tail to the next label. The selection is at least 25ms long and is centered at the midpoint (or touches the start/end boundaries of the data).
- **Reset selection**: Sets the selection to the whole data.
- **Shrink selection**: Shrinks the selection by 10% on each side, keeping the center fixed. The selection is at least 25ms long.
- **Expand selection**: Expands the selection by 10% on each side, keeping the center fixed. The selection is at most the whole data. If one end is out of bounds, the selection is shifted to fit instead of truncated (unless it cannot fit).
- **Shift selection left (Ctrl+L)**: Shifts the whole selection to the left by its width (until it touches the start of the data), keeping the width fixed.
- **Shift selection right (Ctrl+R)**: Shifts the whole selection to the right by its width (until it touches the end of the data), keeping the width fixed.

### Movement menu

- **Step forward (Ctrl+F)**: Moves the cursor forward by 5ms, bound by the selection.
- **Step backward (Ctrl+B)**: Moves the cursor backward by 5ms, bound by the selection.
- **Shift forward/backward**: Shifts the selection just like "Shift selection right/left", but keeps the cursor at the same relative position inside the selection. If the cursor is not inside the selection, it is set to the start of the selection.
- **Cycle forward/backward**: Continuously shifts the cursor forward/backward, wrapping around the selection boundary. Currently the playback speed is always 1x (synchronized with actual time) and the frame rate is always 50 FPS.
- **Reflective cycling**: Continuously shifts the cursor forward; if it hits one boundary, moves in the opposite direction.
- **Stop cycling (Ctrl+X)**: As it says.

### Label menu

Unlike MVIEW, labels are ordered by their creation, not by their temporal position. However, sorting and reordering is allowed if you prefer some other ordering.

- **Make label**: Opens a dialog to add a new simple label at the end of the labels list. By default it's at the cursor position. A name is required.
- **Edit labels**: Opens a dialog to edit the labels list. Each label has a name, a position (in ms), and an optional note. You can delete and reorder labels. You can also edit the name, position, and note of each label. The position must be between the start and the end of the data.
- **Clear all labels (Ctrl+Y)**: As it says. Shows a confirmation dialog.
- **Export labels**: Exports labels to a `.lab` text file. The format is the same as MVIEW:

  ```plain
  LABEL    OFFSET    NOTE
  {name}   {ms}      {optional note}
  ```

  All separators are tabs.

- **Import labels**: Imports labels from a `.lab` text file. The format is the same as MVIEW (see above). The imported labels are appended to the labels list. Only the `LABEL` and `OFFSET` columns are considered; any subsequent text is ignored (including the note).
- **Save labels**: Saves the labels to the app shared memory (analogous to the MATLAB workspace), with an associated name.
- **Load labels**: Loads the labels from the app shared memory. The loaded labels replace the current labels.
- **Labeling behavior**: TODO

## Navbar

The **Play** button has the exact same functionality as the one in the [play menu](#play-menu).

You can read off and edit the cursor, head, and tail positions, all in milliseconds.

## Temporal view

The temporal view is the right panel. It displays the trajectories as time series, with time on the x-axis and the trajectory value(s) on the y-axis. The first plot is the _framing trajectory_ specified with the `--framing` [argument](#command-line-arguments). It always displays the full data. The current selection is highlighted. The cursor and labels are also visible.

All remaining plots are the _temporal display trajectories_ specified with the `--temporal-disp-trajs` [argument](#command-line-arguments) and customizable via the ["Temporal layout" dialog](#view-menu). They only display the data within the current selection. The cursor and labels are also visible.

Currently, the trajectories' colors are determined by the `COLOR` field in the dataset or otherwise arbitrarily. Color selection will be supported. If the data is multidimensional, each dimension is plotted separately, with x being the most opaque and z being the most transparent (with a legend). The zero line is shown as a dashed line if in the visible y-range.

Currently, each axis' y-range is adaptive to the range of the trajectory data. [Common scaling](#view-menu) will be supported.

For the spectrogram's parameters, see [spectrogram](#spectrogram).

You can drag the selection in the framing trajectory to shift it, or drag its boundaries to resize. Double-clicking resets it to the entire data.

You can click in the temporal display trajectories to set the cursor, or drag to move the cursor. You can also drag a label to move it, or double-click one to edit it. You can right-click to create a label at the position (this invokes the custom labeling procedure).

## Spatial view

The spatial view is the top-left panel. It displays the locations of all spatial signals at the cursor position (and is not affected by which ones are temporally displayed). The plot is 2D or 3D depending on the data's dimensions (configurable via the `--comps` [argument](#command-line-arguments)).

The sensors' colors are consistent with the temporal trajectories' colors.

The axes' ranges are set to contain all spatial movements across all variables.

When the plot is 3D, you can customize the view via the [spatial options](#view-menu). You can also configure display of the spline.

## Spectrogram

TODO
