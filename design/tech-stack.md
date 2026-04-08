# 1. Core language/runtime layer

## Python (backend + Tk frontend)

* **Python 3.11+**

  * Reason: better performance, typing, asyncio improvements

* **Standard library (heavily used)**

  * `asyncio` → async backend server + job handling
  * `http.server` (prototype) or replaced by FastAPI later
  * `dataclasses` → core models
  * `typing` → schema typing
  * `json` → protocol serialization
  * `pathlib` → file handling
  * `wave`, `audioop` → basic audio handling
  * `sqlite3` → optional lightweight persistence
  * `multiprocessing` → heavy computation isolation
  * `logging` → structured logs
  * `uuid` → session/artifact IDs

## JavaScript (React frontend)

* **Node.js (LTS)**
* **pnpm**

  * faster, deterministic installs

---

# 2. Backend (Python)

## 2.1 Web framework

Recommended:

* **FastAPI**

  * Async-first
  * Automatic OpenAPI docs
  * Pydantic integration
  * Easy WebSocket support

Alternatives (if stricter stdlib desired initially):

* `http.server` (prototype only)
* **Starlette** (lighter than FastAPI)

## 2.2 Data validation / schema

* **Pydantic v2**

  * Strong typing for protocol models
  * JSON schema generation
  * Validation for sessions, commands, configs

## 2.3 Numerical / signal processing

* **NumPy**

  * Core array operations

* **SciPy**

  * Signal processing (`scipy.signal`)
  * FFT, filtering, LPC approximations

* **Numba** (optional but highly recommended)

  * Speed up heavy loops (spectrogram, F0, etc.)

* **Pandas** (optional)

  * Only for tabular label/export workflows

## 2.4 Audio processing

* **soundfile** (libsndfile wrapper)

  * Read/write WAV, FLAC, etc.

* **scipy.io.wavfile** (fallback if avoiding external deps)

* Optional:

  * **resampy** (resampling)
  * **librosa (optional)** — only if needed for advanced features

    * but avoid if you want minimal deps

## 2.5 Spectral / F0 / analysis (no Praat)

Implement internally using:

* `scipy.signal.spectrogram`
* FFT via `numpy.fft`
* Autocorrelation (custom or SciPy)
* LPC (can implement or use `scipy.signal.lfilter`-based approach)

Optional helpers:

* **praat-parselmouth** → NOT allowed per your constraint

## 2.6 Backend utilities

* **orjson** (recommended)

  * Fast JSON serialization

* **uvicorn**

  * ASGI server for FastAPI

* **watchfiles**

  * Dev auto-reload

* **rich**

  * CLI output formatting

* **typer**

  * CLI interface (excellent, built on click)

## 2.7 Storage / caching

* **diskcache** (optional)

  * Simple persistent cache for spectrograms etc.

* **SQLite (stdlib)** for:

  * session persistence (optional)
  * artifact indexing

---

# 3. Python frontend (Tk)

## 3.1 GUI

* **tkinter (stdlib)**

  * Core UI

* **ttk (stdlib)**

  * modern widgets

## 3.2 Plotting / visualization

* **matplotlib**

  * Temporal plots
  * Spectrogram rendering
  * Spatial plots (2D/3D via mpl_toolkits)

* Optional:

  * **tkinter canvas custom rendering** (for performance)
  * **pyopengl** (only if you later need performant 3D)

## 3.3 Backend communication

* **httpx**

  * Async HTTP client

* Standard alternative:

  * `urllib.request` (but not recommended)

## 3.4 Async integration

* `asyncio` + Tk loop bridge

  * (custom integration needed)

---

# 4. JavaScript frontend (React)

## 4.1 Core

* **React 18+**
* **Vite**
* **pnpm**

## 4.2 State management

Recommended:

* **Zustand**

  * Simple, minimal, perfect for session state

Alternatives:

* Redux Toolkit (heavier)
* Jotai

## 4.3 Data fetching

* **TanStack Query (React Query)**

  * Handles:

    * caching
    * background updates
    * request deduplication

## 4.4 Visualization

### Temporal plots

* **uPlot**

  * extremely fast time-series rendering

Alternative:

* **Plotly.js** (easier but heavier)

### Spectrogram

* Canvas/WebGL:

  * **regl** or **PixiJS** (optional)
  * or plain `<canvas>` for MVP

### Spatial (2D/3D)

* **Three.js**

  * for 3D trajectories

* **react-three-fiber**

  * React wrapper for Three.js

## 4.5 UI components

* **Radix UI**

  * accessible primitives

* **Tailwind CSS**

  * fast styling

Optional:

* **shadcn/ui** (built on Radix + Tailwind)

## 4.6 Forms / config editing

* **react-hook-form**

  * lightweight form handling

## 4.7 Type safety

* **TypeScript**

  * strongly recommended

---

# 5. Shared protocol / schema

## 5.1 Schema definition

* **JSON Schema**

  * canonical protocol definition

* Generated from:

  * Pydantic models (backend)

## 5.2 Code generation (optional but powerful)

* **datamodel-code-generator**

  * generates TS types from Pydantic

* OR:

  * **openapi-typescript**

## 5.3 Validation (frontend)

* **zod**

  * runtime validation of backend responses

---

# 6. CLI / programmatic interface

## CLI

* **typer**
* **rich**

## Programmatic

* Thin Python API wrapping backend calls:

  * uses `httpx` or direct in-process calls

---

# 7. Dev tooling

## Python

* **uv**

  * fast package manager + virtual env

* **ruff**

  * linting + formatting

* **pytest**

  * testing

## JS

* **eslint**
* **prettier**
* **vitest** or **jest**

---

# 8. Packaging / deployment

## Desktop

* **Tauri** (recommended)

  * smaller than Electron
  * can embed Python backend

Alternative:

* Electron

## Backend deployment

* **uvicorn + FastAPI**
* Optional:

  * **Docker**

## Web deployment

* Frontend: static hosting (Vercel, Netlify)
* Backend: server (AWS/GCP/etc.)

---

# 9. Optional performance / advanced tools

These are not required for MVP but useful later:

* **PyTorch / JAX** (if ML features added)
* **WebAssembly (WASM)** for frontend-side computation
* **Arrow / Apache Arrow**

  * efficient columnar data transfer

---

# 10. Minimal viable stack (if you want to trim)

If you want the leanest possible version:

### Backend

* Python
* FastAPI
* NumPy
* SciPy
* Pydantic
* uvicorn

### Python frontend

* tkinter
* matplotlib
* httpx

### JS frontend

* React
* Vite
* Zustand
* uPlot

Everything else is optional.
