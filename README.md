# PyView

Python port of MView

```bash
uv sync
source .venv/bin/activate
```

```bash
python -m pyview ./test_data/S02_data.mat --palate S02_pal --temporal-display AUDIO_SPECT TDx vTDx TDz vTDz
```

## Central concepts

## Command-line arguments

You can run `python -m pyview --help` to see the full list of command-line arguments.

- First, you need to provide a `file` argument pointing to a `.mat` [dataset file](#dataset-format).
- Then, you can optionally provide a `variables` pattern. It uses [`fnmatch`](https://docs.python.org/3/library/fnmatch.html), so you can use `*` to match a sequence of characters and `?` to match a single character. If no variable pattern is provided, then all variables in the dataset file are used.
- Finally, you can provide any number of options:
  - `--palate VAR` (MVIEW `PALATE`): use the variable `VAR` (in the `file`) to plot a palate curve in the spatial view. If specified, the variable must contain a `[n_samples × n_dims]` array of palate points. If unspecified, no palate is plotted.
  - `--pharynx VAR` (MVIEW `PHARYNX`): use the variable `VAR` (in the `file`) to plot a pharynx curve in the spatial view. If specified, the variable must contain a `[n_samples × n_dims]` array of pharynx points. However, per MVIEW compatibility, if the pharynx trace is 2D and the spatial data is 3D, an extra column of zeros will be added as the y-axis. If unspecified, no pharynx is plotted.
  - `--spline TRAJ1 TRAJ2 ...` (MVIEW `SPLINE`): specifies that the trajectories `TRAJ1`, `TRAJ2`, etc. (in each variable) should have a spline fitted in the spatial view. If specified, all names must refer to spatial trajectories. If unspecified, then all spatial trajectories with name starting with `T` are used as default.
  - `--audio TRAJ`: specifies that the trajectory `TRAJ` (in each variable) contains audio data. If specified, the name must refer to a scalar trajectory. If unspecified, then the first audio trajectory is used as the default. If no such trajectory exists, then all audio-related features (spectrogram time-slice, playback, etc.) are disabled.
  - `--framing TRAJ` (MVIEW `FTRAJ`): specifies that the trajectory `TRAJ` (in each variable) should be used for temporal framing. If specified, the name must refer to a scalar trajectory. If unspecified, then the audio trajectory is used as the default framing trajectory, and if no audio trajectory is found, then the first trajectory of any kind is used as the framing trajectory.
  - `--temporal-display SPEC1 SPEC2 ...` (MVIEW `TEMPMAP`): a list of temporal view specifications. Each specification specifies one temporal plot. See [temporal view](#temporal-view) for more details regarding their presentation.
    - If designating an audio trajectory (sampling rate ≥ 5000 Hz): `TRAJ` or `TRAJ_MODIFIER`, where `MODIFIER` can be: `SPECT` (spectrogram), `RMS` (root mean square), `ZC` (zero-crossing rate), `F0` (fundamental frequency). **Note**: unlike MVIEW, we have a strict separation of audio and physiological scalar trajectories.
    - If designating a scalar trajectory (sampling rate < 5000 Hz): `TRAJ` or `TRAJ_MODIFIER`, where `MODIFIER` can be: ``VEL` (velocity), `ABSVEL` (absolute velocity).
    - If designating a spatial trajectory: `TRAJ`, optionally prefixed by `v` or `a`, and optionally suffixed by a subset of `xyz`, indicating if the trajectory should be movement, velocity, or acceleration, and which dimensions to plot. Specifying `xyz` is equivalent to no specification.

    These specification names can also be obtained from the "Temporal layout" dialog.

  - `--spatial-exclude TRAJ1 TRAJ2 ...` (MVIEW `SPATEX`): a list of trajectory names to exclude from the spatial view (they are still included in every other analysis, including the temporal view). If unspecified, then no trajectory is excluded.
  - `--comps COL1 COL2 ...` (MVIEW `IS3D`): equivalent to the dataset `NCOMPS` [field](#dataset-format), but used as a global fallback when the `NCOMPS` field is absent. This global configuration is also used for non-trajectory data, such as palate trace. A single number `N` is equivalent to `0 .. N-1`.
  - `--view ELEV AZIM ROLL` (MVIEW `VIEW`): the initial view of the spatial display, in terms of elevation, azimuth, and roll (in degrees). This is only used if the data is 3D. If unspecified, it defaults to `(0, -90, 0)` (i.e., sagittal section, right view).
  - `--head MS` (MVIEW `HEAD`): the position (in milliseconds) of the left edge of the temporal selection. If specified, it must be a non-negative number less than `--tail - 25`. If unspecified, it defaults to the start of the data (0 ms). It only has an effect on the first opened window; subsequent windows inherit the opening window's selection.
  - `--tail MS` (MVIEW `TAIL`): the position (in milliseconds) of the right edge of the temporal selection. If specified, it must be a non-negative number greater than `--head + 25`. If unspecified, it defaults to the end of the first variable's data. It only has an effect on the first opened window; subsequent windows inherit the opening window's selection.
  - `--sex SEX` (MVIEW `SEX`): the subject's sex. `M` for male; `F` for female. This can be later customized in the 'Configure spectral analysis' dialog, but it affects the default LPC degree. Default is `M`.
  - `--spect-lim HZ` (MVIEW `SPECLIM`): frequency upper limit (Hz) for spectrogram display. This affects the visualization of the spectrograms but does not affect the underlying spectral analysis. Default is the Nyquist frequency.

Note that the framing and audio trajectory discovery is slightly different from MVIEW's; for one, we never special-case the very first trajectory.

The `NAME`, `VLIST` and `VLSEL` arguments are not supported because all of their downstream effects can be easily customized, and they interact poorly with other features (e.g., "Variables" menu, the `variables` argument, etc.). Please let me know if you have a specific use case.

## Dataset format

The `.mat` file contains three levels:

- Variables: each PyView window views one variable.
- Trajectories: each variable contains one or more trajectories, represented as an array of structs.
- Fields: each trajectory struct has required and optional fields.

Only variables that contain structs are considered valid variables. Other variables (those that contain plain arrays) are considered supplementary data. They are only useful if some other [argument](./arguments.md) refers to them:

- `--palate`: looks for a variable containing a `[n_samples × n_dims]` array of palate points.

The following fields are required for each trajectory struct:

- `NAME` (string): trajectory name. Will be uppercased and stripped of underscores. The actual names absolutely do not matter with one quirk: if the `--spline` [argument](#command-line-arguments) is not provided, all spatial trajectories with name starting with `T` will be used as default.
- `SRATE` (float): sampling rate in Hz. The actual sampling rate value only matters in one place: trajectories with `SRATE` ≥ 5000 Hz are considered audio trajectories, and those with `SRATE` < 5000 Hz are considered physiological trajectories.
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
- TODO: `AUDIO` (boolean)?

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
  - **Entire window**: Clone all plots in the current window as a single matplotlib figure. Currently the layout is broken.
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
- **Spectral analysis**: Opens a dialog to configure the spectrogram parameters. These parameters may affect: the cursor spectrum in the bottom left, the temporal analysis in the temporal view (`SPECT`, `RMS`, `ZC`, `F0`), the external spectrum window (TODO), and the **Report** action. Note that the "nudge" setting has been moved to the ["Configure movement"](#movement-menu) dialog.
  - **Analysis window (ms)** (default: 30ms): Configures the window size for the `RMS` and `ZC` temporal analyses, and the window size for the **Report** output.
  - **Number of LPC coeffs** (default: `audio_sampling_rate / 1000 + 8` if female, otherwise `audio_sampling_rate / 1000 + 4`): TODO
  - **# FFT eval points** (default: 256): Configures the frequency resolution of the `SPECT`. Unlike MVIEW, the actual number of FFT samples must be at least the window size in samples.
  - **Averaging window (ms)** (default: 6ms): Configures the analysis window for the `SPECT` (I don't think this is right but this is how it is in MVIEW).
  - **Overlap (ms)** (default: 1ms): Configures the window shift for the `SPECT`.
  - **SPL reference (dB)** (default: 20dB): TODO
  - **Spectral display cutoff (Hz)** (default: `audio_sampling_rate / 2`): Affects visualization only. Configures the ymax of `SPECT` and the xmax of the time-slice spectrograms.
  - **Adaptive pre-emphasis** (default: 0.98): TODO
  - **Active analyses** (default: LPC): TODO
  - **Subject gender** (default: Male): TODO
  - **Spectrogram** (default: wide): Acts as a multiplier for **Averaging window** (and affects `SPECT` only). **Wide** = 1, **Mid 1** = 2, **Mid 2** = 3, **Narrow** = 4. The longer the window, the better the frequency resolution but poorer the temporal resolution.

### View menu

- **Temporal layout**: Configure which trajectories to display in the temporal view. It launches a dialog where you can:
  - Select available trajectories from the left-hand side to add (`>`) to the display area on the right-hand side.
  - Select displayed trajectories from the right-hand side to remove (`x`) from the display area.
  - Select one displayed trajectory from the right-hand side to reorder (`^` and `v`).
  - Select one displayed trajectory from the right-hand side to customize its content. For spatial trajectories, you can choose to display position, velocity, or acceleration, and which dimensions to display. For scalar trajectories, you can choose to apply a temporal analysis (spectrogram, RMS, zero-crossing rate, fundamental frequency, etc.).

  The list of names on the right-hand side are known as "temporal display specifications". They are also used in the `--temporal-display` [argument](#command-line-arguments) and the "Report" output.

- **Set common scaling**: Opens a dialog to configure the y-axis limits for all spatial trajectories.
  - **Adaptive scaling**: Each trajectory has its own y-axis limits, determined by the range of the trajectory data (i.e., matplotlib default auto-scaling logic). New in PyView.
  - Configured spreads: Configure a common spread for all movement/velocity/acceleration trajectories, respectively. The `ymax - ymin` will be equal to that value, leaving an equal margin on the top and bottom.

  By default adaptive scaling is enabled and you cannot configure spreads. When you disable it, the spreads default to `1.1` of the maximum range across all _visible_ trajectories (different from MVIEW, which also considers invisible trajectories and therefore can end up with an excessively large common scale). The values you set (or default) are good for as long as the temporal display remains the same or adaptive scaling remains disabled; the next time you enable and re-disable adaptive scaling, or when you change the temporal display settings, the common scaling will be re-computed.

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
  - **Between labels**: Only has an effect if the cursor is between two labels. Plays the audio between the previous and next labels.
- **Select playback track**: TODO

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

- **Step forward (Ctrl+F)**: Moves the cursor forward by the nudge step size, bound by the selection.
- **Step backward (Ctrl+B)**: Moves the cursor backward by the nudge step size, bound by the selection.
- **Shift forward/backward**: Shifts the selection just like "Shift selection right/left", but keeps the cursor at the same relative position inside the selection. If the cursor is not inside the selection, it is set to the start of the selection.
- **Cycle forward/backward**: Continuously shifts the cursor forward/backward, wrapping around the selection boundary.
- **Reflective cycling**: Continuously shifts the cursor forward; if it hits one boundary, moves in the opposite direction.
- **Stop cycling (Ctrl+X)**: As it says.
- **Configure movement**: Opens a dialog to configure the movement behavior.
  - **Nudge step size (ms)** (default: 5ms): The amount of time to move when stepping forward/backward, in milliseconds. (In MVIEW this also controls the cycling; in PyView you use playback rate and FPS instead.)
  - **Playback rate** (default: 1; i.e., synchronized with real time): How fast the simulated motion is relative to real time when cycling. For example, if the playback rate is 2, then the cursor moves twice as fast as real time, so a 10-second selection would take 5 seconds to cycle through.
  - **Frame rate (FPS)** (default: 20): The frame rate of the simulated motion when cycling, in frames per second. You can get the "nudge step size" for cycling by `1000 / frame_rate_fps * playback_rate` ms. So by default it is 50ms. You don't want the frame rate too large (especially if it exceeds your screen's refresh rate!), because it can cause performance issues, and practically the signal probably have a sampling rate of ~100 Hz anyway. The animation tends to go out of sync at 30 FPS (sorry Python isn't really efficient for real-time stuff).

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

You can drag the selection in the framing trajectory to shift it, or drag its boundaries to resize. Double-clicking resets it to the entire data.

All remaining plots are the _temporal display trajectories_ specified with the `--temporal-display` [argument](#command-line-arguments) and customizable via the ["Temporal layout" dialog](#view-menu). They only display the data within the current selection. The cursor and labels are also visible, should they be inside the selection.

Currently, the trajectories' colors are determined by the `COLOR` field in the dataset or otherwise arbitrarily. Color selection will be supported. If the data is multidimensional, each dimension is plotted separately, with x being the most opaque and z being the most transparent (with a legend).

Following MVIEW behavior, the velocity/acceleration of the whole vector (e.g., `vTD`) only displays the magnitude (and is therefore unsigned), while the velocity/acceleration of specific dimensions (e.g., `vTDx`, `vTDxy`) displays each separate dimension (and is signed).

If multiple curves are plotted, each curve will be re-centered (`curve - (max(curve) + min(curve)) / 2`) to avoid inflating the y-range.

By default, each axis' y-range is adaptive to the range of the trajectory data (using matplotlib's default auto-scaling). You can also configure [common scaling](#view-menu) for spatial trajectories, so that all movement/velocity/acceleration trajectories each share the same y-span.

If a single curve is plotted and it is not movement (i.e., scalar, velocity, or acceleration), the zero line will be indicated as a dashed line should it be within the y-span of the plot.

Unlike MVIEW, all scalar trajectories with sampling rate >5000Hz—not just audio—support spectrogram display (this was nominally supported in MVIEW but in reality it seems to be sketchy). Short Time Fourier Transform (STFT) is used. You can customize its data using the following [spectral analysis](#data-menu) options:

- **# FFT eval points**
- **Averaging window**
- **Overlap**
- **Spectral display cutoff**
- **Spectrogram**

You can click in the temporal display trajectories to set the cursor, or drag to move the cursor. You can also drag a label to move it, or double-click one to edit it. You can right-click to create a label at the position (this invokes the custom labeling procedure).

## Spatial view

The spatial view is the top-left panel. It displays the locations of all spatial signals at the cursor position. It is not affected by which ones are temporally displayed; to exclude certain signals, you can use the `--spatial-exclude` [argument](#command-line-arguments). The plot is 2D or 3D depending on the data's dimensions (configurable via the `--comps` [argument](#command-line-arguments)).

The sensors' colors are consistent with the temporal trajectories' colors.

The axes' ranges are set to contain all spatial movements across all variables, not just the current variable (unlike MVIEW).

If the `--palate` or `--pharynx` [argument(s)](#command-line-arguments) are configured, they will be plotted in the spatial view as lines.

If the `--spline` [argument](#command-line-arguments) is configured, the spline curve will be plotted in the spatial view. You can configure its display via the [**Hide spline**](#view-menu) action.

When the plot is 3D, you can customize the view via the [spatial options](#view-menu) or the `--view` [argument](#command-line-arguments).

## Spectrogram

TODO
