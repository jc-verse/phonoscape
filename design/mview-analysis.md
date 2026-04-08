## 0\. Overview

`mview` is a MATLAB desktop application for interactive visualization of multiple concurrently recorded data streams. Its core purpose is to load a synchronized set of trajectories, derive useful secondary signals, and let the user inspect them in linked temporal, spatial, spectral, and labeling views. The file is implemented as a single large entry-point function, `mview(varargin)`, with many action branches and a substantial set of local helper functions. Architecturally, it is a command-dispatch GUI controller wrapped around a persistent per-window state structure stored in the figure’s `userdata`.

At the top level, the program accepts several kinds of input. The primary one is a MAVIS-compatible array of structs whose minimum required fields are `NAME`, `SRATE`, and `SIGNAL`, where `SIGNAL` is `[nSamps x nDims]`. It also accepts a string naming a variable, possibly with wildcards; a cell array of variable names; or a raw numeric 3D array `[nSamps x nDims x nChan]`, which it converts into multiple trajectories with an assumed sample rate of 250 Hz. If called with no arguments, it either brings existing MVIEW windows to the front or shows help. If called as `mview abort`, it closes all viewers.

The architectural pattern is event-driven. `mview(varargin)` first interprets the first argument either as input data or as an action string, then routes execution through a large `switch action` block. Actions include lifecycle operations such as `INIT`, `CLOSE`, `ABORT`, and `ABOUT`; configuration actions such as `CFGSPEC`, `CFGTEMP`, `CFGSPAT`, and `SETSCALING`; user interaction actions such as `DOWN`, `UP`, `MOVECUR`, `MOVESEL`, `MOVESPAT`, and `MOVESPEC`; data/reporting actions such as `REPORT`, `GETCFG`, `SAVESEL`, and `CALLFCN`; and label-management actions such as `MAKELBL`, `LEDIT`, `LEXPORT`, `LIMPORT`, `LSAVE`, `LLOAD`, and `LSETPROC`. This makes the file functionally similar to an old-style MATLAB app framework where the main function doubles as both constructor and callback target.

The central runtime object is the `state` struct created during `INIT`. It holds all GUI handles, the loaded data, display configuration, cursor and selection positions, label state, playback state, plotting-procedure state, and derived display metadata. Important fields include `DATA`, `TPANELS`, `SPATIALA`, `SPECTRA`, `CURSOR`, `HEAD`, `TAIL`, `LABELS`, `TEMPMAP`, `SPREADS`, `SPECGRAM`, `AUTO`, `FMTS`, `LPROC`, `LPSTATE`, `PPROC`, `PPSTATE`, `VIEW`, `SPATEX`, `FTRAJ`, and `IS3D`. State is stored on the figure and mutated by callbacks, with `SetBounds` and `SetCursor` acting as the main refresh functions.

The data-processing pipeline begins with `ParseData`, which normalizes the dataset and computes derived channels. For multidimensional trajectories, it expands the original coordinates into a fixed layout containing position, per-axis velocity, total velocity magnitude, per-axis acceleration, and total acceleration magnitude. It also computes common scaling ranges for movement, velocity, and acceleration, determines the shortest concurrent duration across all streams, identifies which channels are spatial trajectories, and infers whether the data should be treated as truly 3D. It adds or normalizes metadata fields such as `SPREAD`, `NCOMPS`, and optionally `ANGLES`. This derived-signal generation is one of the most important pieces of the tool, because much of the later plotting logic assumes the enriched representation produced by `ParseData`.

`mview` also supports pre-processing and extension hooks. During initialization, user-specified `DPROC` functions are called on the dataset before plotting. The code comments list built-in examples such as `MDP_LIPAPERTURE`, `MDP_PALDIST`, and `MDP_STRIPREF`. Similarly, `LPROC` hooks let the caller provide custom labeling behavior, and `PPROC` hooks let the caller add custom plotting behavior. These hook procedures can be passed as strings or as cell arrays that bundle a function name with arguments. The `GETCFG` output explicitly persists these extension points in the configuration structure, which shows that extensibility is part of the intended API, not a private implementation detail.

The visible GUI has four main regions. First, there is a spatial panel on the left, which displays movement trajectories in 2D or 3D and can optionally overlay a palate trace, pharynx line, spline connections, and fitted circles. Second, there is a framing panel at the top right, showing the framing trajectory and the currently selected time span. Third, there is a spectral panel on the left middle/bottom for cross-sectional spectra and a zoom panel for a short waveform segment around the cursor. Fourth, there is a large stack of temporal panels on the right that display the chosen signals over time, plus a transparent cursor axis layered on top for linked interaction. These regions are created in `INIT` using `axes`, `uicontrol`, `uicontextmenu`, and helper builders like `InitTraj` and `InitControls`.

The temporal display is especially configurable. The `TEMPMAP`/`MAP` mechanism defines which trajectories appear, in which order, and in what transformed form. The syntax supports prefixes like `v` and `a` for velocity and acceleration, component suffixes like `x`, `y`, and `z`, and monodimensional modifiers like `_SPECT`, `_F0`, `_RMS`, `_ZC`, `_VEL`, and `_ABSVEL`. The parser for this mini-language is `ParseTempMap`, which converts a display token into a trajectory index, a modification code, and a component mask. The same mechanism is used both for layout configuration and for extracting the currently displayed values at the cursor.

The default behavior for temporal panels is sensible but domain-specific. If `TEMPMAP` is not provided, the code initially displays all loaded trajectories, and if the first trajectory has a sample rate above 1000 Hz, it also inserts a spectrogram panel for that first trajectory. This strongly suggests the common use case is “audio plus kinematic channels,” where the first track is speech or another high-rate signal and later tracks are lower-rate movement measurements. The framing trajectory can also be changed with `FTRAJ`, so the data stream used for the top selection panel is configurable.

Spectral analysis is built in. `ComputeSpectra` computes an LPC-based spectral envelope and formant estimates around the current cursor location. `ComputeF0wrapper` and `ComputeF0local` provide pitch estimation using a modified autocorrelation method. `SetCursor` updates the spectral cross-section display in the side panel, and `PlotSpectra` can open a more detailed external spectral figure. The configuration dialog invoked by `CFGSPEC` exposes analysis parameters such as FFT frame size, LPC order, analysis window length, averaging window and overlap, pre-emphasis, spectral cutoff, active analysis modes, spectrogram style, and sex-dependent heuristics for F0 estimation. The GUI therefore combines visualization with moderate signal-analysis functionality.

Selection and cursor interaction are first-class concepts. The user has a cursor time in milliseconds and a selected interval `[HEAD, TAIL]`. Clicking and dragging in the framing panel moves the selection or its edges. Clicking in a temporal panel moves the cursor. Manual text entry into cursor/head/tail fields is also supported. `SetBounds` refreshes all displays to the current selection, including limiting temporal axes, recomputing the spectrogram, and updating custom plot procedures. `SetCursor` refreshes cursor-linked displays such as the zoomed waveform, spectral cross-section, spatial position, and value readouts. Auto-update can be toggled, and when disabled, selection changes can be applied manually with `UPDATE`.

The spatial display supports both inspection and derived plots. The spatial panel can show current positions, optional spline connections between selected trajectories, optional fitted circles in 2D, multiple canned camera views in 3D, free rotation, and “Hue Plot” or “History Plot” overlays over the selected time interval. This makes the spatial side more than just a static side panel; it is a linked exploratory view of the movement subspace. The `SPATEX` parameter also lets callers exclude particular movement signals from the spatial display without removing them from the dataset entirely.

Label handling is extensive. Labels are stored as structs with fields such as `NAME`, `OFFSET`, `VALUE`, `HOOK`, and runtime plotting handles. Labels can be created interactively, edited, moved, deleted, saved to the workspace, loaded from the workspace or `.mat` files, exported to a `.lab` text format, and imported back. The code can also load labels from Praat TextGrid tiers when `LABELS` is passed as a filename/tier pair. There is support for both default labeling behavior and custom labeling procedures through `LPROC`. Selection can be snapped to the pair of labels bracketing the cursor. This is a substantial subsystem rather than a minor annotation feature.

Audio playback is also integrated. The “Play” menu provides several scopes: current selection, entire file, from head to cursor, from cursor to tail, a 150 ms window around the cursor, or the interval between the two labels bracketing the cursor. There is also support for playing an alternate track when multiple same-rate tracks exist. Playback uses `audioplayer` stored in a base-workspace `PLAYER` variable, with cleanup handled by `PLAYX` and `CLOSE`.

The public API surface is broader than just `mview(data, ...)`. There are several useful callable sub-actions. `mview('CALLFCN','ComputeF0',state)` returns F0, `mview('CALLFCN','ComputeSpectra',state)` returns spectral data and formants, `mview('CALLFCN','FitCircle',p)` fits a circle through three points, `mview('CALLFCN','GetVals',state)` returns currently displayed values and labels, and `mview('CALLFCN','ParseTempMap',...)` exposes the panel-map parser. `mview('GETCFG', state)` returns a full configuration struct suitable for later reuse, and `mview('VIEW', [az el])` can set the spatial view of the first open viewer from the command line. Many other actions are technically invocable from code, but these are the ones that look intentionally reusable.

The configuration object returned by `GETCFG` is effectively the serializable settings schema for the application. It includes figure position, spectral-analysis parameters, zoom size, pre-emphasis, contrast, auto-update flag, formant-tracking state, label-procedure state, plotting hooks, palate and pharynx geometry, analysis mode, spectrogram multiplier, temporal map, sex flag, audio scaling, spectral display limit, spline configuration, circle visibility, spatial view, spatial exclusions, 3D override, framing trajectory, and per-trajectory colors. This provides a stable way to save and replay display setups across sessions.

A concise summary of the accepted input data format is as follows. The minimal required trajectory struct contains `NAME`, `SRATE`, and `SIGNAL`. Optional fields recognized during initialization include `LABELS`, `COLOR`, `CONTOURS`, `SPREAD`, `NCOMPS`, and `ANGLES`. The first trajectory often acts as the framing and spectral source. Movement trajectories are expected to have 2 or 3 columns before derived channels are added; if they have more than 3 columns, columns beyond the first three are moved into `ANGLES`. Labels, if present, may come either as a top-level explicit argument or embedded inside the data.

From a software-engineering perspective, the main strengths of the design are that it is self-contained, highly interactive, domain-aware, and extensible through `DPROC`, `LPROC`, and `PPROC`. Its weaknesses are also clear: the entire application is packed into one large MATLAB function with string-based callbacks and hidden figure state, so maintainability and testability are limited. The action names form an implicit internal API, but there is no strict separation among model, view, and controller. Even so, the internal structure is consistent: `INIT` builds state, helper functions perform computation and widget creation, and `SetBounds`/`SetCursor` serve as the central redraw/update mechanisms.

## 1\. Product purpose

The software is an interactive viewer for multiple concurrently recorded data streams. Its purpose is to let a user load a synchronized set of signals, inspect them together over time, analyze audio-like channels spectrally, inspect movement-like channels spatially, annotate the data with labels, and export selections, labels, and saved viewing configurations.

The replacement does not need to preserve the original MATLAB architecture or layout, but it must preserve the user-visible capabilities and workflows. A user must be able to treat the loaded dataset as one synchronized recording session containing multiple trajectories or channels, each with a name, a sample rate, and sample data.

## 2\. High-level user experience

A typical session should feel like this.

The user opens one synchronized dataset containing several named signals. Some signals may be audio or other scalar time series. Others may be 2D or 3D movement trajectories. The software presents a shared time domain over all channels and lets the user define a current cursor position and a selected interval. Moving the cursor or changing the selected interval updates all linked views consistently.

The user can inspect the data in several complementary ways:

- A temporal view of selected channels over the chosen time window.
- A spatial view of movement channels, including history over the selected interval.
- A spectral view at the current cursor location for an audio-like framing channel.
- A short zoomed waveform view around the cursor.
- A label layer that marks times of interest and can be edited interactively or generated by procedures.

The user can customize which signals are shown, in what transformed form, and in what order. They can play back the audio in several scopes, compute pitch and formants, inspect numeric values at the cursor, create or modify labels, save selections as new datasets, export labels to disk, import labels from disk or Praat TextGrid, and save the current display configuration for later reuse.

## 3\. Core user concepts

Any replacement should expose these concepts clearly, even if with different terminology.

- A **dataset** is a synchronized collection of named trajectories.
- A **trajectory** is one recorded stream with a name, sample rate, and signal matrix.
- A **framing trajectory** is the main scalar channel used for top-level time framing, spectral analysis, zoomed waveform display, and playback defaults. In practice this is often the first, audio-like channel.
- A **cursor** is the current time position in milliseconds.
- A **selection** is a time interval with a start and end in milliseconds.
- A **label** is an annotation tied to a time offset, optionally with a name, note, value payload, and source hook.
- A **display mapping** is the user’s chosen list of trajectories or derived views shown in the temporal display, including modifiers such as spectrogram, F0, RMS, zero crossing, velocity, and acceleration.
- A **configuration** is a saved bundle of view and analysis settings that can be applied to a future session.

## 4\. Accepted inputs

### 4.1 Primary dataset input

The software must accept a synchronized dataset whose minimal schema is an array of trajectory objects with these required fields:

- `NAME`: trajectory name, such as `AUDIO`
- `SRATE`: sampling rate in Hz
- `SIGNAL`: trajectory samples as a matrix `[nSamps x nDims]`

This is the canonical input form and must be fully supported.

### 4.2 Alternate dataset input forms

To preserve original functionality, the replacement should also accept these convenience forms:

- A string identifying a dataset variable by name.
- A wildcarded string that may match multiple variables or files.
- A list of variable names.
- A raw numeric array shaped `[nSamps x nDims x nChan]`, which must be treated as multiple trajectories and assigned a default sample rate of 250 Hz unless the new system defines a comparable compatibility rule.

These forms are convenience loaders. Even if the new application uses file pickers or other loading flows, the underlying compatibility behavior should be retained.

### 4.3 Optional per-dataset or per-session inputs

The software must support these optional inputs, whether embedded in the dataset or passed separately:

- A saved configuration object.
- A set of labels.
- A label-generation procedure.
- A list of data-preprocessing procedures.
- A list of plotting procedures.
- A palate trace.
- A pharynx line.
- A subject sex or equivalent F0-heuristic selector.
- A temporal display map.
- A framing trajectory selection.
- A spatial exclusion list.
- A 3D override flag.
- Spline or polyline connectivity instructions among trajectories.
- A saved color assignment for trajectories.
- Initial selection start and end times.

### 4.4 Optional dataset enrichments

The original software recognizes several optional fields in the incoming data. A replacement should preserve support for these concepts:

- `LABELS`: embedded labels associated with the dataset.
- `COLOR`: preferred display color for a trajectory.
- `CONTOURS`: aligned contour data, for example ultrasound contours.
- `SPREAD`: preferred plotting range.
- `NCOMPS`: declared number of active components.
- `ANGLES`: extra columns beyond X/Y/Z, treated as auxiliary signals rather than spatial coordinates.

### 4.5 Label sources

Labels must be loadable from at least these sources:

- Explicit label structures.
- A numeric vector of offsets, which should be converted into anonymous labels.
- A Praat TextGrid file and tier specification.
- A saved labels variable or file.
- Embedded labels already attached to the dataset.

### 4.6 Auxiliary geometry inputs

The software must accept:

- A palate trace as a polyline in 2D or 3D.
- A pharynx line in 2D.
- Optional contour sequences aligned in time.

These are visualization aids and should be overlaid in the spatial view or equivalent.

## 5\. Data interpretation rules

### 5.1 Concurrency and duration

All loaded trajectories are treated as concurrently recorded streams. The effective session duration is the duration of the shortest compatible signal. The software must synchronize all operations on that shared time domain.

### 5.2 Scalar versus movement channels

A trajectory with one component is treated as monodimensional. A trajectory with two or three components is treated as movement data. Movement data should support derived kinematic views. If a third component exists, the software must allow either treating it as true Z or suppressing it by override.

### 5.3 Derived kinematic signals

For movement trajectories, the tool must compute or expose derived signals equivalent to:

- Position components X, Y, and optionally Z.
- Per-axis velocity.
- Velocity magnitude.
- Per-axis acceleration.
- Acceleration magnitude.
- The exact internal formulae may differ in a rewrite, but the user-facing capability to inspect those derived signals must remain.

### 5.4 Audio-like channels

Audio-like scalar channels should support waveform display, zoomed local display, playback, spectrogram display, pitch estimation, RMS and zero-crossing derived views, and LPC/DFT spectral cross-sections. The original program effectively assumes the framing trajectory is often an audio signal.

## 6\. What the user can do

### 6.1 Load and reopen data

The user can open a dataset directly, open by symbolic name, choose among matching datasets, or step through a list of datasets while preserving a compatible viewer configuration.

### 6.2 Inspect synchronized signals over time

The user can view multiple signals simultaneously over a selected time interval. The chosen signals can include raw scalar channels, raw movement components, spectrograms, F0 tracks, RMS tracks, zero-crossing tracks, velocity traces, absolute velocity traces, and movement-derived velocity or acceleration components. The user can reorder these views and choose which components are active.

### 6.3 Inspect spatial movement

The user can inspect movement trajectories in 2D or 3D, see current positions at the cursor, show history over the selected interval, optionally color the history by time progression, overlay fixed anatomical guides such as palate and pharynx, draw connections among chosen trajectories, fit a circle in 2D to selected points, and choose among several views or free rotation in 3D.

### 6.4 Move the cursor and change the selection

The user can:

- Move the cursor directly.
- Type a cursor value.
- Drag the selected interval.
- Adjust the start or end of the selected interval.
- Reset the full selection.
- Set selection bounds from the current cursor.
- Shrink, expand, and shift the selection by defined operations.
- Set the selection to the interval between the two labels bracketing the cursor.

All linked views must update consistently when the cursor or selection changes.

### 6.5 Step or cycle through time

The user can step the cursor forward or backward by a configurable nudge size, shift the selection window by its own width, and run automatic cursor cycling forward, backward, or reflectively between the current selection bounds.

### 6.6 Listen to audio

The user can play:

- The selected interval.
- The whole file.
- The region from selection head to cursor.
- The region from cursor to selection tail.
- A short fixed-duration segment centered on the cursor.
- The interval between the two labels bracketing the cursor.
- An alternate track, if appropriate.

### 6.7 Perform signal analysis

At the cursor or over the selected region, the user can access:

- Spectral cross-sections.
- LPC and DFT analyses.
- Pitch estimation.
- Formant estimation and optional formant tracking on the spectrogram.
- RMS.
- Zero crossings.
- Spectral center-of-gravity style measures.
- Current displayed values of non-audio trajectories at the cursor.

The replacement does not need to replicate the exact original algorithms unless strict numerical compatibility is desired, but it must preserve the availability of these analyses and the general meaning of the results.

### 6.8 Configure analysis and display behavior

The user can configure:

- Analysis window size.
- FFT evaluation size.
- LPC order.
- Averaging window and overlap.
- Pre-emphasis and adaptive pre-emphasis behavior.
- Spectral display cutoff.
- Spectrogram style from wideband to narrowband.
- Which analyses are active.
- F0 heuristics that depend on speaker sex or equivalent selection.
- Contrast of the spectrogram.
- Common scaling for movement, velocity, and acceleration traces.
- Whether updates happen automatically or manually.

### 6.9 Create and edit labels

The user can:

- Create labels at the cursor.
- Create labels silently or with annotation.
- Edit label name, offset, and note.
- Move labels in time.
- Delete individual labels or clear all labels.
- Inspect and edit labels from a list.
- Import and export labels.
- Save labels into the current environment.
- Load labels from external sources.
- Use custom label procedures instead of the default behavior.

### 6.10 Save and clone work products

The user can:

- Save the current selection as a new dataset.
- Save everything except the current selection as a new dataset.
- Save the current configuration.
- Duplicate the temporal display, spatial display, or full window for presentation or printing.
- Switch among multiple viewers or multiple datasets.

## 7\. Required generated outputs

The software must be able to generate the following persistent or semi-persistent outputs.

### 7.1 Exported labels file

A text-based label export file with at least these columns:

- `LABEL`
- `OFFSET`
- `NOTE`

In the original program this uses a `.lab` file with tab-separated fields. A replacement may use a different serialization format, but it should remain possible to export and import a simple human-readable label list with at least those fields.

### 7.2 Saved labels object

A label collection saved in an environment-native object form, preserving label name, offset, value payload, and hook/source metadata, excluding ephemeral GUI handles.

### 7.3 Saved configuration object

A configuration object sufficient to restore the user’s working display and analysis setup, including at least:

- Window or view state.
- Temporal display map.
- Analysis parameters.
- Label procedure selection and state.
- Plotting procedure selection.
- Color assignments.
- Spatial view and exclusions.
- Framing trajectory selection.
- Spline and auxiliary-geometry settings.
- Audio scaling and spectral settings.

### 7.4 Saved selection dataset

A newly generated dataset representing either the selected interval or the complement of the selected interval. It must preserve visible signals and include adjusted labels where relevant. The original behavior also stores provenance describing the source name and original selection bounds; the replacement should preserve that concept.

### 7.5 Cloned display windows or exportable snapshots

The original tool can duplicate views into new windows for copying or printing. A replacement should preserve the ability to produce presentation-friendly standalone renderings of the temporal view, the spatial view, or the complete current scene.

## 8\. Label model requirements

A label must support at least these semantic fields:

- A display name, possibly empty.
- A time offset in milliseconds.
- An optional value payload.
- An optional hook or note identifying source or attached metadata.

The tool must preserve ordered labels by offset. New labels should be inserted in time order. Duplicate label suppression should exist at least for exact duplicate cases of time, name, and value. Labels may be grouped or enriched by custom procedures.

## 9\. Temporal display mapping requirements

The user must be able to specify which trajectories appear in the temporal display using a compact mapping language or an equivalent structured configuration. That mapping must support these user-visible cases:

- A raw scalar signal.
- A spectrogram of a scalar signal.
- An F0 track.
- An RMS track.
- A zero-crossing track.
- A scalar-velocity track.
- A scalar absolute-velocity track.
- A raw movement trajectory using chosen components.
- Movement velocity using chosen components or overall magnitude.
- Movement acceleration using chosen components or overall magnitude.

The original syntax uses modifiers like `AUDIO_SPECT`, `TTy`, and `vTTy`. A rewrite may define a different syntax, but it must preserve the same expressive range.

## 10\. Extension requirements

The original tool allows user-supplied procedures in three categories. A replacement should keep extension points with equivalent semantics.

- A **data preprocessing extension** can derive new trajectories or modify the dataset before viewing begins.
- A **labeling extension** can control how labels are created, drawn, imported, exported, and configured.
- A **plotting extension** can add auxiliary plots that respond to selection changes and viewer lifecycle events.

The exact plugin API can be redesigned, but the product must preserve the fact that advanced users can extend preprocessing, labeling, and plotting behavior without modifying the core viewer.

## 11\. Persistence and compatibility requirements

The software should be able to reopen a dataset together with a previously saved configuration, saved labels, and optional auxiliary geometry such as palate and pharynx traces. The original loader also auto-detects companion objects like `cfg`, `pal`, `pha`, and `labels` when loading from a named file. A replacement should preserve the usability goal that saved artifacts can travel with the dataset and be reapplied with minimal user effort.

## 12\. Non-functional behavioral requirements

The following user-visible behaviors matter and should be preserved.

- Linked views must remain synchronized by time.
- The cursor and selection must use milliseconds as the primary user time unit.
- The effective session duration must be clipped to the shortest concurrent signal.
- Movement displays must support common scaling across comparable traces.
- Large selections may suppress expensive visualizations like spectrograms rather than freezing the application.
- Auto-update should be optional.
- Multiple open viewers should be supported.
- A no-argument invocation or equivalent action should reopen or foreground existing viewers rather than always creating a new one.

## 13\. Out-of-scope implementation details

This spec does not require preserving:

- The single-file MATLAB structure.
- Figure `userdata` state storage.
- String-based callbacks.
- Specific axis positions or menu hierarchy.
- Specific internal formulas where only the user-facing meaning matters.
- MATLAB-specific workspace semantics, as long as equivalent loading, saving, and session workflows are offered.

## 14\. Minimal acceptance checklist

A new implementation is functionally complete if a user can do all of the following:

- Load a multi-trajectory synchronized dataset with names, sample rates, and signals.
- View scalar and movement trajectories over time with a shared cursor and selected interval.
- Inspect movement spatially in 2D or 3D with optional overlays and history.
- Inspect scalar audio-like channels with spectrogram, spectrum, zoomed waveform, F0, and formant-related functionality.
- Create, move, edit, import, export, save, and reload labels.
- Save the current selection or the complement as a new dataset with adjusted labels.
- Save and restore a full viewer configuration.
- Play audio over several user-selectable scopes.
- Customize the temporal display mapping and analysis settings.
- Extend preprocessing, labeling, and plotting with user-defined procedures.
