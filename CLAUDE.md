# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PPX** is a cross-platform desktop toolkit combining Vue 3 + Element Plus (frontend) with Python + Pywebview (backend). It delivers PDF tools, Excel manipulation, system utilities, and cryptographic data storage—packaged as native applications for Windows, macOS, and Linux via PyInstaller.

## Key Commands

### Development Setup & Maintenance
- `pnpm run init` - Full initialization: clears caches, installs GUI dependencies, creates Python venv, seeds local keys
- `pnpm run clean` - Removes build artifacts and node_modules (run before fresh init on Windows issues)

### Running & Development
- `pnpm run start` - Launches both Vue dev server (Vite hot reload) and Python backend in parallel
- `pnpm run dev` - Frontend only; Vite dev server at http://localhost:5173
- `pnpm run startos` - Backend only; Python pywebview with nodemon auto-reload

### Building & Packaging
- `pnpm run pre` - Pre-release build with console output; append `:windows`, `:macos`, `:linux` for platform
- `pnpm run build` - Production build and installer; append `:windows`, `:macos`, `:linux` for platform
- `pnpm run build:pure` - Single .exe (Windows only); faster startup than folder mode
- `pnpm run build:cef` - Windows build with embedded Chromium (CEF) for compatibility
- `pnpm run build:folder` - Windows build as folder + installer (default; faster than pure)

### Database Migrations (SQLite only)
- `m="description" pnpm run alembic` - Generate and apply Alembic migration; exports SQL to `static/db/`

## Architecture

### Frontend (`gui/`)
- **Framework**: Vue 3 + Element Plus + Vite
- **Entry**: `gui/src/main.js` → `gui/src/App.vue`
- **Components**: `gui/src/components/` organized by feature (pdf, excel, seal, system)
- **Build Output**: `gui/dist/` → packaged into `pyapp/spec/` for embedding
- **Style**: Scoped SCSS in each `.vue` file, PascalCase filenames (e.g., `PdfTool.vue`)

### Backend (`api/` + `pyapp/`)
- **Entry Point**: `main.py` (boots Config, DB, and API, creates pywebview window)
- **API Layer**: `api/api.py` inherits from feature modules (System, Storage, PDF, Excel, Seal)
  - Methods exposed to JS via `window.pywebview.api.<methodName>()`
  - Only basic Python types (int, str, dict, etc.) serialize to JavaScript
- **Feature Modules**: `api/*.py` (pdf.py, excel.py, system.py, storage.py, seal.py)
  - Methods follow snake_case convention; often prefixed with module name (e.g., `pdf_merge`, `system_getAppInfo`)
- **Configuration**: `pyapp/config/config.py` holds app name, version, appISSID, database type, and environment paths
- **Database**:
  - TinyDB (default, `api/db/json/orm.py`) for files <10MB
  - SQLite (opt-in, `api/db/sql/orm.py` + Alembic migrations) for larger data
  - Both store test data in `Config.staticDir`, production data in `Config.appDataDir`

### Key Paths
- **Dev Port Detection**: `.ppx-dev-port` (JSON file written by Vite, read by pywebview to auto-detect hot-reload server)
- **Static Assets**: `static/` (packaged into binary; includes cache, db seed, CSS)
- **Build Output**: `build/` (intermediate PyInstaller artifacts; remove before rebuilding)
- **Python Virtual Environment**: `pyapp/pyenv/pyenv/` (Windows) or `pyapp/pyenv/` (Unix)

## Development Workflow

1. **Initial Setup**: `pnpm run init` (handles platform-specific venv creation)
2. **Daily Dev**: `pnpm run start` (runs Vite + Python concurrently; HMR via nodemon)
3. **Frontend-Only Iteration**: `pnpm run dev` in one terminal, keep Python running
4. **Test Changes**: Manual end-to-end testing inside the desktop window; check terminal logs for Python tracebacks
5. **Database Changes** (SQLite): Modify `api/db/sql/models.py` → `m="reason" pnpm run alembic` → regenerate artifacts
6. **Pre-Flight Checks**: Run `pnpm run pre:<platform>` to catch packaging issues before production build

## Important Notes

### Pywebview & Platform Specifics
- **Windows (Normal Mode)**: Uses native Edge/WebView2; install [EdgeWebView2Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/) if not present
- **Windows (CEF Mode)**: Embeds Chromium v66+; larger package (~60MB) but works on older systems
- **macOS**: Single WebKit engine; x86_64-built apps run on both x86_64 and M-series, M-series builds only on M
- **Linux**: Ubuntu 22.04+ tested; dpkg-based installer

### Data Storage & Security
- Use `pyapp/db/json/getKeyDB.py` to initialize the TinyDB keystore; do not edit JSON manually
- Run `pnpm run init` to regenerate keys, not manual edits
- Leverage `api/system.py` helpers (e.g., `system_pyOpenFile`, file dialogs) for cross-platform consistency
- Test data lives in `Config.staticDir`; production data in `Config.appDataDir`

### Packaging & Versioning
- **GUID Rule**: Before first init, set `appISSID = ''` in `pyapp/config/config.py`; let init auto-generate and **never modify**—otherwise Windows uninstaller will duplicate, not replace
- **Version**: Update in `pyapp/config/config.py` (e.g., `appVersion = 'V1.0.0'`)
- **Auto-Update**: Configured to check GitHub Releases; respects semantic versioning

### Common Issues
- **White Screen on Startup**: Ensure .NET Framework 4.0+ and WebView2 installed; fallback to `pnpm run build:cef`
- **Missing Modules/DLLs in Packaged App**: Add to `addDll` or `addModules` in `pyapp/spec/getSpec.py`
- **Chinese Paths on Windows**: Causes pyinstaller + pywebview failures; use ASCII-only paths

## Code Style & Conventions

- **Python**: PEP 8; snake_case methods; docstrings for API methods
- **Vue**: PascalCase file names; 2-space indentation; scoped styles per component
- **Git Commits**: Short, imperative Chinese (e.g., `优化访问 TinyDB 数据库的逻辑`); include module/feature scope
- **PR Bodies**: Problem statement, testing steps (`pnpm run start`, `pnpm run pre`, etc.), screenshots for UI changes
- **Branch Management**: Keep rebased on main; avoid noisy merges

## Testing Strategy

1. **Manual E2E**: `pnpm run start` → interact with desktop window → monitor terminal for errors
2. **Pre-Build**: `pnpm run pre:<platform>` with console output before production release
3. **DB Test**: Verify TinyDB reads/writes in `Config.staticDir` during dev; production data persists in `Config.appDataDir`
4. **Cross-Platform**: Use GitHub Actions (`.github/workflows/main.yml`) for simultaneous Windows/macOS/Linux builds

## Useful Development Patterns

### Frontend ↔ Backend Communication
```javascript
// From JS to Python (Promise-based)
window.pywebview.api.system_getAppInfo().then(res => console.log(res))
```

```python
# From Python to JS
def system_py2js(window):
    info = {'appName': 'PPX'}
    window.evaluate_js(f"window['handleInfo']({json.dumps(info)})")
```

### Feature Module Template
Create new feature in `api/`:
1. `api/myfeature.py` with class `MyFeature` and methods like `myfeature_doSomething()`
2. Inherit in `api/api.py`: `class API(System, Storage, PDF, Excel, Seal, MyFeature)`
3. Call from Vue via `window.pywebview.api.myfeature_doSomething()`

### Database Queries
- **TinyDB**: `db.table('users').search(User.name == 'Alice')`
- **SQLite**: Use Alembic for schema; SQLAlchemy ORM for queries
