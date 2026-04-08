## Assumptions

This plan assumes a first end-to-end implementation by one engineer or a very small team, at 30 hours per week, with the goal of reaching a working vertical slice early and then filling in preserved functionality. It also assumes the architecture chosen in the previous step: versioned session-oriented backend, language-neutral JSON protocol, frontend/backend separation, and three product modes built on the same core backend.

The plan is organized to reduce integration risk. The earliest weeks focus on the protocol, canonical data model, backend session lifecycle, and a thin frontend shell. Then it adds the core workflows in the order users most depend on them: load data, view synchronized traces, move cursor and selection, labels, analysis, exports, then packaging for desktop, CLI, and web.

## Deliverables by milestone

By the end of week 4, there should be a usable vertical slice: open a dataset, create a session, display temporal traces, move cursor and selection, and fetch synchronized view data.

By the end of week 8, the full core viewer should exist: temporal, spatial, zoom, labels, saved configs, selection exports, and CLI/programmatic usage.

By the end of week 12, the first feature-complete beta should exist: spectral analysis, label import/export, plugin hooks, desktop packaging, web deployment flow, tests, and documentation.

## Week 1: foundations, protocol, and repository structure

**Goal:** establish the contract that all later work depends on.

**Work items**  
Define repository structure for backend, frontend, shared schema docs, CLI, and packaging.  
Define canonical domain models: dataset, trajectory, label, config, session state, view model, artifact, command result.  
Define protocol versioning rules.  
Write JSON schemas or equivalent typed contracts for:  
session creation,  
session snapshot,  
cursor/selection,  
labels,  
temporal mapping,  
config,  
artifact references,  
error responses.  
Define backend service boundaries: session service, dataset service, processing service, label service, config service, artifact service, plugin service.  
Define transport strategy for local and remote operation.  
Set up CI, linting, formatting, test harness skeleton, and API documentation skeleton.

**Dependencies**  
None.

**Acceptance criteria**  
There is a written architecture spec in the repo with all canonical models and service boundaries.  
JSON schemas exist for the core request/response objects.  
A developer can run validation against example payloads.  
The repo has build/test/lint commands for backend and frontend shells.  
At least one mock session snapshot can be generated and validated end to end.

## Week 2: backend skeleton and session lifecycle

**Goal:** create the backend runtime that can own sessions and speak the protocol.

**Work items**  
Implement backend server skeleton with routing for HTTP mode.  
Implement in-process service interfaces using the same request/response models.  
Implement session creation, get session, close session.  
Implement basic session store with in-memory persistence.  
Implement startup parameter handling: dataset source placeholder, config placeholder, labels placeholder, selection defaults.  
Implement standard error handling and logging.  
Implement artifact registry skeleton.  
Add health/version endpoints.  
Write unit tests for session lifecycle.

**Dependencies**  
Week 1 schemas and service boundaries.

**Acceptance criteria**  
A client can create a session and receive a valid session snapshot.  
A client can fetch the same session snapshot later by ID.  
A client can close a session.  
Errors are returned in a standardized schema.  
Tests cover session creation, invalid payloads, and teardown.

## Week 3: dataset ingestion and canonical normalization

**Goal:** backend can actually ingest supported inputs and normalize them.

**Work items**  
Implement canonical dataset model in code.  
Implement ingestion for primary structured dataset input.  
Implement ingestion for raw numeric array input equivalent.  
Implement loading adapters for file-based dataset inputs.  
Implement optional embedded fields handling: labels, colors, contours, NCOMPS, ANGLES, palate, pharynx.  
Compute dataset summary: duration, trajectory metadata, kinds, dimensions, sample rates.  
Implement source metadata/provenance tracking.  
Implement validation rules and good error messages for malformed data.  
Add tests with representative scalar, 2D, and 3D datasets.

**Dependencies**  
Week 2 backend and session lifecycle.

**Acceptance criteria**  
A dataset with `NAME`, `SRATE`, and `SIGNAL` can be ingested into a session.  
Optional metadata fields are preserved where applicable.  
The backend returns a normalized dataset summary with stable IDs.  
Malformed inputs fail with specific validation errors.  
Test fixtures cover at least scalar audio-like, 2D movement, and mixed datasets.

## Week 4: temporal data service and minimal frontend vertical slice

**Goal:** first usable synchronized viewer.

**Work items**  
Implement temporal mapping model and parser equivalent to the old expressivity.  
Implement time window queries for visible traces.  
Implement multiresolution or basic decimated trace extraction for temporal display.  
Implement cursor and selection update commands.  
Implement backend generation of temporal view model.  
Implement a minimal frontend that can:  
create/open a session,  
render temporal tracks,  
move cursor,  
set selection,  
refresh on backend snapshots.  
Implement frontend state management around session snapshots and commands.

**Dependencies**  
Weeks 2–3.

**Acceptance criteria**  
A user can load a dataset and see temporal traces in the frontend.  
Changing cursor updates the session and re-renders correctly.  
Changing selection updates the visible time window.  
Multiple tracks stay synchronized in time.  
The vertical slice works over HTTP with the same backend used locally.

## Week 5: spatial view and derived kinematics

**Goal:** preserve movement inspection workflows.

**Work items**  
Implement backend derivation of movement velocity and acceleration channels.  
Implement 2D/3D movement classification and override support.  
Implement spatial exclusion logic.  
Implement spatial view model generation:  
current positions at cursor,  
selection history traces,  
palate/pharynx overlays,  
contour overlays,  
view/camera parameters,  
spline/polyline overlays.  
Implement frontend spatial renderer for 2D and minimal 3D.  
Implement cursor-linked updates between temporal and spatial view.

**Dependencies**  
Week 3 dataset normalization and week 4 session/temporal interaction.

**Acceptance criteria**  
Movement datasets show current position linked to cursor.  
Selection history can be rendered in spatial view.  
Velocity/acceleration derived channels are available through the protocol.  
2D and 3D datasets render correctly, with 3D override respected.  
Palate and pharynx overlays appear when present.

## Week 6: zoom view, cursor values, and report infrastructure

**Goal:** support detailed local inspection around cursor.

**Work items**  
Implement zoomed waveform excerpt service around cursor.  
Implement cursor value extraction for displayed non-audio tracks.  
Implement structured report endpoint returning summary metrics scaffold.  
Implement frontend zoom renderer and values panel.  
Implement shared refresh pathways so cursor changes update temporal, spatial, zoom, and values together.  
Refine caching for cursor-local requests.

**Dependencies**  
Weeks 4–5.

**Acceptance criteria**  
Cursor movement updates a zoomed local signal excerpt.  
The frontend can display current values for displayed trajectories.  
A structured report endpoint returns cursor time, selection bounds, and placeholder/partial metrics in a stable schema.  
Synchronized update latency is acceptable on representative test data.

## Week 7: labels core workflow

**Goal:** preserve annotation workflows.

**Work items**  
Implement canonical label model and ordered insertion.  
Implement create, update, move, delete, clear commands.  
Implement duplicate suppression rules.  
Implement label list retrieval and selection-to-bracketing-pair operation.  
Implement frontend label overlays in temporal view.  
Implement frontend label panel/editor.  
Implement backend support for label style metadata without frontend handles.  
Add tests for ordering, movement, editing, deletion, and bracketing behavior.

**Dependencies**  
Weeks 2–4.

**Acceptance criteria**  
A user can create, edit, move, and delete labels through the frontend.  
Labels persist in backend session state and survive reload of session snapshot.  
Selection can be set to the pair of labels bracketing cursor.  
Label order is always by offset.  
Duplicate exact labels are rejected or coalesced consistently.

## Week 8: config save/load, selection export, and headless workflows

**Goal:** make the system useful outside the interactive GUI.

**Work items**  
Implement config save/load endpoints and canonical config serialization.  
Implement save-selection and save-complement backend operations.  
Implement artifact generation for saved dataset outputs.  
Implement provenance metadata in generated selection datasets.  
Implement CLI commands for:  
open session,  
headless selection export,  
save config,  
load config,  
basic label save/load.  
Implement thin programmatic API wrappers over backend services.  
Add integration tests for headless workflows.

**Dependencies**  
Weeks 2–7.

**Acceptance criteria**  
A user can save a config from an interactive session and load it into a new one.  
A user can export the selected interval as a new dataset artifact.  
A user can export the complement of the selection as a new dataset artifact.  
The CLI can perform those same operations without GUI.  
The programmatic wrapper can create a session and invoke the same workflows.

## Week 9: spectral analysis, spectrograms, and audio playback preparation

**Goal:** preserve audio-analysis functionality.

**Work items**  
Implement backend spectrogram generation service, initially for selected windows.  
Implement spectral cross-section endpoint at cursor.  
Implement F0 estimation endpoint.  
Implement formant estimation endpoint or structured placeholder with same semantics.  
Implement RMS and zero-crossing derived scalar views.  
Implement audio excerpt generation/preparation endpoints for playback scopes.  
Implement frontend spectrum/spectrogram views and controls.  
Add backend controls for analysis parameters: window size, LPC/DFT flags, cutoff, overlap, pre-emphasis, sex heuristic.

**Dependencies**  
Weeks 3–6, preferably week 8 config handling too.

**Acceptance criteria**  
A user can view a spectrogram for an audio-like framing trajectory.  
A user can request a spectral cross-section at cursor.  
F0, RMS, and zero-crossing views are available through temporal mapping.  
Audio playback requests return playable excerpts or streams for all required scopes.  
Analysis parameters affect returned results and persist in config.

## Week 10: import/export interoperability and artifact polish

**Goal:** preserve external data exchange.

**Work items**  
Implement label export format equivalent to `.lab`.  
Implement label import for that format.  
Implement Praat TextGrid import path.  
Implement artifact download endpoints and metadata.  
Implement export of reports/configs/labels with protocol versioning.  
Polish dataset load flow for named variables, file bundles, and companion artifacts where relevant.  
Implement frontend export/import UI.  
Add tests for round-trip label import/export and config persistence.

**Dependencies**  
Weeks 7–9.

**Acceptance criteria**  
Labels can be exported and imported with no loss of core fields.  
Praat TextGrid labels can be imported into the session.  
Artifacts are downloadable via stable backend references.  
Saved configs can round-trip cleanly.  
Users can perform these actions from frontend, CLI, and programmatic modes where appropriate.

## Week 11: plugin architecture and extension hooks

**Goal:** preserve DPROC/LPROC/PPROC-style extensibility in the new architecture.

**Work items**  
Implement backend plugin registry and manifest schema.  
Implement plugin interfaces for:  
data preprocessing,  
label behavior,  
analysis/plot overlays.  
Implement config-driven plugin activation.  
Implement safe plugin execution and error reporting.  
Implement frontend display of plugin-contributed overlays or capabilities.  
Ship one example plugin in each category or two realistic examples total.  
Write developer docs for plugin authors.

**Dependencies**  
Weeks 3, 7, and 9 especially.

**Acceptance criteria**  
A preprocessing plugin can augment a dataset during ingestion.  
A label plugin can participate in label workflows through backend-defined actions.  
An analysis/plot plugin can contribute structured overlay data to a view model.  
Plugin failures are isolated and reported cleanly.  
A new plugin can be added without changing frontend core code.

## Week 12: desktop packaging, web hardening, and beta stabilization

**Goal:** deliver the first coherent product across all target modes.

**Work items**  
Package desktop app with embedded/local backend and frontend shell.  
Harden web deployment path: auth placeholder if needed, upload limits, session expiry, artifact cleanup.  
Polish CLI UX and help text.  
Add end-to-end tests across local and HTTP transports.  
Add performance checks on representative large datasets.  
Write user documentation and developer setup docs.  
Run bug-fix and stabilization pass.  
Prepare beta release checklist.

**Dependencies**  
Weeks 1–11.

**Acceptance criteria**  
Desktop mode launches and connects to the same backend protocol successfully.  
Web frontend communicates with backend over HTTP and supports the main workflows.  
CLI help and commands are documented and usable.  
Core end-to-end flows pass in CI:  
load dataset,  
move cursor/selection,  
create/edit labels,  
save config,  
export selection,  
run spectral analysis.  
A beta release can be installed and exercised by another developer without ad hoc setup.

## Dependency summary

Weeks 1–2 are foundational and block everything else.

Week 3 blocks all meaningful viewer work because all later features depend on canonical dataset ingestion.

Week 4 is the first integration point and blocks effective frontend progress.

Week 5 depends on week 3 normalization and week 4 session/view plumbing.

Week 6 depends on week 4 temporal interaction and benefits from week 5\.

Week 7 depends on basic session and temporal overlay infrastructure from weeks 2 and 4\.

Week 8 depends on stable session, labels, and config schemas from weeks 2–7.

Week 9 depends on dataset ingestion, selection/cursor services, and config support.

Week 10 depends on label/config/export infrastructure from weeks 7–9.

Week 11 depends on stabilized backend services so plugin APIs do not churn excessively.

Week 12 depends on near-complete functionality in all earlier weeks.

## Suggested hour allocation pattern per week

A reasonable split for most weeks is:

12 hours implementation of the primary backend component.  
8 hours frontend or transport integration.  
5 hours tests.  
3 hours docs/schema updates.  
2 hours buffer for debugging and refactoring.

For week 12, shift more time into testing, packaging, and stabilization.

## Critical path

If schedule pressure appears, the critical path is:

Week 1 protocol and models.  
Week 2 session backend.  
Week 3 dataset ingestion.  
Week 4 temporal vertical slice.  
Week 7 labels.  
Week 8 config/export/headless.  
Week 9 spectral/audio.  
Week 12 packaging and stabilization.

The most deferrable items are advanced plugin polish, rich 3D interaction polish, and nonessential UX improvements, but not the underlying protocol support for them.

## Definition of “feature-complete enough to replace the old tool”

The project is ready for serious user testing when all of these are true:

A dataset can be loaded in desktop, CLI, and web-backed modes.  
Temporal and spatial synchronized inspection works.  
Cursor and selection semantics are preserved.  
Labels can be created, edited, imported, exported, and used to define selections.  
Configs and selection exports work.  
Audio/spectral workflows are available.  
The frontend/backend boundary is enforced, with all heavy computation and file access on the backend.
