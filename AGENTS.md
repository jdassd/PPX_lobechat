# Repository Guidelines

## Project Structure & Module Organization
PPX pairs a Vue desktop shell with a Python backend. `gui/` hosts the Vue 3 + Element Plus app (entry `src/main.js`, shared widgets in `src/components/`). `pyapp/` keeps runtime config, Alembic migrations, packaging specs, and nodemon settings, while `main.py` boots pywebview and surfaces `api/` helpers to JS. Treat everything under `build/` and `static/` as generated artifacts and regenerate them through scripts rather than hand-editing.

## Build, Test, and Development Commands
- `pnpm run init`: cleans caches, installs `gui` dependencies, provisions `pyapp/pyenv`, and seeds local keys.
- `pnpm run dev`: serves the Vue app through Vite with hot reload for UI-only iterations.
- `pnpm run start`: runs `run-p dev startos` so the Vue frontend and pywebview host start together.
- `pnpm run pre` / `pnpm run build`: create pre-release or production installers; add `:macos`, `:windows`, or `:linux` for platform-specific output.
- `pnpm run alembic m="add_user_table"`: generates/applies DB migrations and exports SQL into `static/db/`.

## Coding Style & Naming Conventions
Follow the house Vue style: PascalCase filenames (`BtnUpdate.vue`), 2-space indentation, and scoped styles inside each SFC. Favor small composition functions or shared components instead of deep relative imports. Python modules mirror PEP 8 with docstrings (`api/system.py` is canonical); snake_case methods often start with `system_` or `storage_`.

## Testing Guidelines
Rely on layered manual testing: run `pnpm run start`, exercise end-to-end flows inside the desktop window, and monitor terminal logs for Python stack traces. Before distributing, run `pnpm -C gui run build` for the SPA and `pnpm run pre:<platform>` for the packaged app. Every DB change requires an Alembic migration plus regenerated artifacts in `static/db/`; confirm TinyDB test data lives under `Config.staticDir` while production data targets `Config.appDataDir`.

## Commit & Pull Request Guidelines
Recent history shows short, imperative Chinese commits (e.g., `优化访问 TinyDB 数据库的逻辑`); keep that tone and scope each commit to one change. Reference issue IDs or affected modules in the body and call out platform impacts when relevant. PRs need a brief problem statement, testing notes (`pnpm run start`, `pnpm run pre`, etc.), and screenshots or logs for UI tweaks; keep branches rebased on `main` to avoid noisy merges.

## Security & Configuration Tips
Secrets and update channels live in `pyapp/config` plus the TinyDB keystore created by `pyapp/db/json/getKeyDB.py`; rerun `pnpm run init` instead of editing JSON manually, and use `api/system.py` helpers (`system_pyOpenFile`, selection dialogs) so pywebview permissions stay consistent across platforms.
