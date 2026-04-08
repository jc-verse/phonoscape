## 0\. Architecture design goals

The system should preserve the user experience and capabilities of the original tool, but treat visualization and interaction as a frontend concern and data access, computation, persistence, and export as backend concerns.

The architecture should satisfy four deployment styles with the same core protocol and backend semantics:

- A library/API used from code, which can spawn the GUI.
- A CLI with equivalent capabilities.
- A desktop application.
- A web-based application with a JavaScript frontend calling a backend over HTTP.

The most important architectural principle is that the frontend must never need direct access to raw files or internal analysis code. It should operate on declarative models, commands, and serialized results.

## 1\. High-level architecture

The system should be decomposed into five layers.

- The first layer is the **frontend shell**, which exists in multiple forms: desktop UI, browser UI, and optionally an embedded GUI launched from programmatic or CLI invocation. Its responsibilities are rendering views, collecting user input, maintaining ephemeral local UI state, and calling backend APIs.
- The second layer is the **session API**, a transport-agnostic contract that defines sessions, commands, state snapshots, dataset schemas, labels, configuration objects, exports, and analysis requests. This is the stable boundary between frontend and backend.
- The third layer is the **application backend**, which owns sessions, loading, validation, derived data generation, label persistence, export generation, plugin execution, and all expensive analysis.
- The fourth layer is the **data/processing engine**, which implements domain logic: temporal mapping, derived kinematics, spectral analysis, label operations, audio extraction/playback preparation, selection trimming, import/export adapters, and plugin execution.
- The fifth layer is the **storage/integration layer**, which handles file access, object serialization, uploaded assets, temporary artifacts, dataset registries, and external format adapters such as Praat TextGrid.

## 2\. Core principle: frontend/backend contract

The frontend should only know these categories of things:

- A session identifier.
- Serializable state snapshots.
- Serializable commands and events.
- Serializable view models for rendering.
- Artifact references for downloads or streaming.
- The backend should own these categories of things:
- Raw dataset storage and loading.
- Computation of derived signals.
- Persistence of labels and saved configurations.
- Import/export and artifact generation.
- Authorization, validation, plugin execution, and resource management.

This means the frontend should not compute spectrograms, derived velocities, or trimmed datasets as required behavior. It may do optional local conveniences such as panning animations or cursor hover previews, but the source of truth is always the backend.

## 3\. Standardized serialization format

The system needs a language-neutral serialization format. The safest default is JSON for control-plane objects and metadata, with explicit support for binary payloads where needed.

A good design is:

JSON for all commands, session state, schemas, configs, labels, analysis parameters, and view descriptions.

Binary blobs for dense numeric arrays, audio, and image tiles. These can be transferred as:  
base64 inside JSON for small payloads,  
or referenced as separate resources via URLs, object IDs, or multipart transport for larger payloads.

For HTTP mode, use:  
JSON over REST for standard request/response operations,  
server-sent events or WebSocket for live updates if needed,  
binary endpoints for array chunks, audio segments, and exported artifacts.

For desktop and programmatic embedded mode, use the exact same JSON schemas over:  
in-process calls,  
local IPC,  
or loopback HTTP.

The contract should be versioned. Every top-level message and saved artifact should include a protocol version.

## 4\. Recommended communication model

Use a session-based command/state model.

The frontend creates or opens a session.

The backend returns a session snapshot with current dataset, configuration, selection, cursor, available views, capabilities, and artifact references.

The frontend sends commands such as:  
set cursor,  
set selection,  
change layout mapping,  
request spectrogram,  
create label,  
save selection,  
export labels,  
load config,  
play audio segment.

The backend applies each command and returns either:  
an updated session snapshot,  
a command result object,  
or a job handle for long-running operations.

This model works across all three major modes and avoids frontend dependence on backend internals.

## 5\. Deployment modes

### 5.1 Programmatic invocation

A library should expose a function similar in spirit to `mview(data, params)` but redesigned around the new architecture.

Examples of host-language APIs might conceptually look like:

`open_viewer(dataset=..., config=..., labels=..., mode="desktop")`

`create_session(dataset=..., config=...)`

`export_selection(session_id, format=...)`

The important thing is that programmatic invocation should be able to:

- Create a session from in-memory data or file references.
- Pass startup configuration.
- Spawn a GUI attached to that session.
- Operate headlessly for batch export or analysis.

The programmatic API should be a thin wrapper around the same session/backend contract.

### 5.2 CLI

The CLI should mirror the programmatic entrypoints. It should support:

- Open dataset in GUI.
- Open with config, labels, palate, pharynx, and startup selection.
- Run headless exports.
- Import/export labels.
- Save trimmed selections.
- Print reports or analysis outputs.
- Start a local backend server.
- Launch desktop shell attached to a local session.

The CLI is especially important for reproducibility and automation.

### 5.3 Desktop app

The desktop app should bundle:

- A backend runtime, local or embedded.
- A frontend shell.
- A local persistence/artifact directory.
- A loopback or in-process session transport.

The desktop app should behave like a single product to the user, but internally still respect the frontend/backend boundary.

### 5.4 Web-based mode

The web mode should use:

- A JavaScript frontend.
- A backend server reachable over HTTP.
- Optional WebSocket or SSE for live session updates.

The browser should never need local file-system assumptions beyond upload/download. File reading and processing happen server-side after upload or after referencing remote data sources the server can access.

## 6\. Backend subsystem design

The backend should be organized into clear services.

### 6.1 Session service

Responsible for creating, loading, updating, and destroying viewer sessions.

A session contains:  
dataset reference,  
resolved configuration,  
cursor,  
selection,  
loaded labels,  
derived-data cache metadata,  
view mapping,  
analysis settings,  
plugin state,  
artifact registry,  
permissions/capabilities.

The session service is the main orchestrator.

### 6.2 Dataset service

Responsible for accepting inputs, validating schemas, normalizing datasets, and exposing data access methods.

It should support:  
in-memory dataset ingestion,  
file-based loading,  
named dataset lookup,  
wildcard or collection selection,  
optional embedded assets like labels/config/palate/pharynx.

It should normalize all inputs into a canonical internal dataset model.

### 6.3 Processing service

Responsible for:  
derived kinematic channels,  
spectrogram generation,  
F0 estimation,  
formant-related analysis,  
RMS and zero-crossing derived traces,  
selection trimming,  
cursor value extraction,  
report generation.

This service should be stateless or near-stateless except for explicit caches.

### 6.4 Label service

Responsible for:  
label creation, editing, deletion, movement,  
ordered insertion,  
duplicate suppression,  
import/export,  
Praat TextGrid ingestion,  
plugin-managed labels,  
selection-to-label-pair operations.

### 6.5 Configuration service

Responsible for:  
startup configuration parsing,  
saving/restoring viewer configs,  
compatibility validation across sessions,  
default resolution.

### 6.6 Artifact/export service

Responsible for generating:  
label export files,  
saved selection datasets,  
saved configs,  
render snapshots if supported,  
downloadable reports,  
audio excerpts if needed.

Artifacts should be immutable and content-addressable when practical.

### 6.7 Plugin service

Responsible for sandboxing and executing the equivalents of DPROC, LPROC, and PPROC.

In the new architecture, plugins should be backend-only. The frontend should see only declared capabilities and outputs.

## 7\. Frontend subsystem design

The frontend should be a pure interaction and rendering layer.

It should maintain only ephemeral state such as:  
current viewport,  
hover position,  
drag state,  
open dialogs,  
local cached tiles or traces,  
optimistic UI state if used.

It should render from backend-provided models rather than reconstructing domain logic itself.

The frontend should include components conceptually equivalent to:

- A session shell.
- A temporal view renderer.
- A spatial view renderer.
- A spectrum/spectrogram renderer.
- A zoomed waveform renderer.
- A labels editor/panel.
- A configuration editor.
- An artifact/export panel.
- A dataset/browser panel if needed.

None of these should require direct knowledge of file formats or analysis algorithms.

## 8\. Canonical data model

The new architecture needs explicit, serialized domain models.

### 8.1 Dataset model

A canonical dataset object should include:

`dataset_id`  
`name`  
`duration_ms`  
`trajectories`  
`metadata`  
`auxiliary_geometry`  
`embedded_labels`  
`source_info`

Each trajectory should include:

`trajectory_id`  
`name`  
`sample_rate_hz`  
`dimensions`  
`kind` such as scalar, movement2d, movement3d, auxiliary  
`units`  
`channel_schema`  
`storage_ref`  
`display_defaults`

Raw arrays should usually be referenced by `storage_ref` rather than fully embedded in every response.

### 8.2 Label model

A label should include:

`label_id`  
`name`  
`offset_ms`  
`note`  
`value`  
`hook`  
`style`  
`group`  
`source`  
`readonly`

No frontend-only handle state should appear in the canonical model.

### 8.3 Configuration model

A config should include:

analysis settings,  
temporal display mapping,  
framing trajectory,  
spatial options,  
scaling settings,  
cursor/selection defaults if desired,  
color assignments,  
plugin configuration,  
visibility flags,  
export preferences.

### 8.4 Session state model

A session snapshot should include:

`session_id`  
`dataset_summary`  
`config`  
`cursor_ms`  
`selection`  
`labels_summary`  
`available_actions`  
`view_models`  
`analysis_status`  
`artifacts`  
`warnings`

## 9\. View model design

The backend should provide view models that are already semantically resolved but not pixel-rendered.

### 9.1 Temporal view model

Should specify:  
which tracks are shown,  
their order,  
their semantic type,  
their y-scaling,  
their axis labels,  
their visible time range,  
trace data references,  
image/tile references for spectrogram-like layers,  
annotation overlays.

The frontend then renders these generically.

### 9.2 Spatial view model

Should specify:  
2D or 3D mode,  
visible trajectories,  
current cursor positions,  
history traces for selection,  
optional palate/pharynx/contour overlays,  
optional spline/polyline overlays,  
camera/view parameters.

### 9.3 Spectral view model

Should specify:  
frequency axis limits,  
active analysis overlays,  
curve data references,  
formant markers,  
analysis parameters used.

### 9.4 Zoom view model

Should specify:  
waveform excerpt around cursor,  
time width,  
center marker.

### 9.5 Labels view model

Should specify:  
visible labels in range,  
label ordering,  
selection-relative markers,  
editing permissions,  
style hints.

## 10\. Command API

A clean architecture needs a command set independent of UI details.

Examples of core commands:

`CreateSession`  
`OpenDataset`  
`CloseSession`  
`SetCursor`  
`SetSelection`  
`SetTemporalMapping`  
`SetFramingTrajectory`  
`SetSpatialOptions`  
`SetScaling`  
`SetAnalysisConfig`  
`RequestViewRefresh`  
`CreateLabel`  
`UpdateLabel`  
`DeleteLabel`  
`ClearLabels`  
`ImportLabels`  
`ExportLabels`  
`SaveLabels`  
`LoadLabels`  
`SaveConfig`  
`LoadConfig`  
`SaveSelection`  
`SaveComplement`  
`RequestReport`  
`RequestCursorValues`  
`PlayAudio`  
`CloneViewArtifact`  
`RunPluginAction`

Each command should have a request schema and a typed result schema.

## 11\. API transport design

For interoperability, define the protocol once and expose it three ways.

### 11.1 In-process API

For embedded programmatic use, the host library can call backend methods directly, but request and response objects should still use the same schemas.

### 11.2 IPC/local transport

For desktop, use local HTTP, Unix socket, named pipe, or other IPC. HTTP is simplest because it also matches web mode.

### 11.3 Remote HTTP API

For web mode, expose RESTful endpoints such as:

`POST /sessions`  
`GET /sessions/{id}`  
`POST /sessions/{id}/commands/set-cursor`  
`POST /sessions/{id}/commands/set-selection`  
`POST /sessions/{id}/commands/create-label`  
`POST /sessions/{id}/exports/labels`  
`POST /sessions/{id}/exports/selection`  
`GET /artifacts/{artifact_id}`

For long-running work, use jobs:

`POST /jobs`  
`GET /jobs/{id}`

## 12\. Handling large numeric data

Dense time-series and spectrograms can be large. The architecture should avoid shipping raw full-resolution arrays unnecessarily.

Use multiresolution and windowed access.

The backend should expose:  
trace decimation for visible windows,  
spectrogram tiles or images for selected ranges,  
cursor-local excerpts for zoom and analysis,  
history traces limited to selection.

The frontend requests only what it needs for the visible range and resolution.

This is especially important in web mode.

## 13\. File input and artifact generation model

Since file reading and generation must stay backend-side, all file interactions should follow this pattern:

Frontend asks to upload, open, import, or export.

Backend receives a file upload, file reference, or dataset identifier.

Backend parses or generates the artifact.

Backend returns either:  
a success object with imported content applied to session,  
or an artifact reference for download.

This includes:  
datasets,  
TextGrid files,  
label files,  
saved configurations,  
saved trimmed datasets,  
rendered clones or snapshots.

## 14\. Programmatic and CLI entrypoint design

The system should present a unified conceptual interface.

A programmatic call and a CLI call should both map to the same startup request model.

A startup request should support:  
dataset source,  
config source,  
labels source,  
palate/pharynx source,  
selection head/tail,  
framing trajectory,  
temporal map,  
mode,  
whether to launch UI,  
whether to run headless.

That lets all modes remain consistent.

## 15\. Plugin architecture in the new design

The original MVIEW has DPROC, LPROC, and PPROC. In the new architecture, these should become explicit backend plugins.

Recommended redesign:

Data plugins transform or augment datasets during ingestion or on demand.

Label plugins implement custom label logic, import/export, and rendering metadata.

Analysis/plot plugins contribute computed overlays or sidecar outputs.

Plugins should declare:  
name,  
version,  
capabilities,  
accepted input schema,  
returned output schema,  
configuration schema.

The frontend should not execute plugins directly. It should only call backend plugin actions and render returned view metadata.

## 16\. Session lifecycle

A session lifecycle should look like this.

- Create session from dataset and startup parameters.
- Backend validates input and resolves default config.
- Backend computes lightweight summaries immediately.
- Backend lazily computes heavy artifacts when requested.
- Frontend interacts by commands.
- Backend persists labels/config/exports as requested.
- Session closes explicitly or expires.
- In desktop mode, sessions may be autosaved locally.
- In web mode, sessions may be temporary unless persisted intentionally.

## 17\. Cross-mode parity requirements

All major functionality should be available in all modes, but exact UX can differ.

Programmatic and CLI modes must support headless operations.

Desktop mode should support the richest local workflow.

Web mode should preserve all essential functionality, even if audio playback and large file upload handling are implemented differently under the hood.

The underlying protocol and backend semantics should remain the same.

## 18\. Suggested implementation split by language

Because the protocol is language-neutral, teams can choose different implementations.

A practical stack could be:

- Backend in Python, Rust, Julia, MATLAB-compatible service, or C++ depending on numeric and file-compatibility needs.
- Desktop frontend in Electron, Tauri, Qt/QML, or native toolkit.
- Web frontend in TypeScript/React or another JS framework.
- CLI in the backend language or as a thin wrapper.

The architecture remains valid regardless of these choices because the protocol is the stable center.

## 19\. Non-functional requirements

The new architecture should support:

- Protocol versioning.
- Reproducible saved artifacts.
- Deterministic session snapshots where practical.
- Graceful degradation for very large selections.
- Backend-side caching of expensive computations.
- Authentication/authorization for web mode if multi-user.
- Isolation of file access and plugin execution.
- Structured logging and auditability of commands.

## 20\. Minimal concrete recommendation

If choosing one reference architecture, I would recommend this:

- A backend-centered session server exposing a versioned JSON/HTTP API.
- A canonical dataset/config/label schema.
- Binary array resources exposed by artifact IDs or chunked endpoints.
- A frontend that renders backend-provided view models and sends commands.
- A desktop app that runs the same backend locally and talks to it over loopback HTTP.
- A CLI and programmatic API that are thin wrappers over the same session service.

This gives the strict separation you want, preserves all functionality, and keeps desktop, CLI, programmatic, and web deployment aligned.
