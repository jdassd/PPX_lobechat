# Repository Guidelines

## Project Structure & Module Organization
- `gui/` contains the Vue 3 + Element Plus frontend (Vite). Source lives in `gui/src/` and static assets in `gui/public/`.
- `pyapp/` hosts the Python backend and packaging assets (e.g., `pyapp/package/`, `pyapp/spec/`, `pyapp/db/`).
- `main.py` is the desktop app entry point.
- `static/` contains bundled assets and database artifacts used at runtime.
- `docs/` and `api/` hold project documentation and API-related materials.

## Build, Test, and Development Commands
- `pnpm -C ./gui run dev` starts the frontend dev server (Vite).
- `pnpm -C ./gui run build` builds the production frontend bundle into `gui/dist/`.
- `pnpm run init` installs dependencies and sets up the Python virtual env plus initial data.
- `pnpm run start` runs frontend dev plus the desktop backend via OS-specific scripts.
- `pnpm run build` produces a packaged app; see OS-specific variants in `package.json` (e.g., `build:windows`).

## Coding Style & Naming Conventions
- Frontend linting/formatting lives in `gui/.eslintrc.cjs` and `gui/.prettierrc.js`.
- Prettier uses 2-space indentation, single quotes, no semicolons, and LF line endings.
- Keep file and component names consistent with existing modules; avoid introducing new naming patterns.

## Testing Guidelines
- No dedicated test framework or test directory is configured.
- If you add tests, document the runner and provide a `pnpm` script for it.

## Commit & Pull Request Guidelines
- Recent commits are short, imperative summaries (often in Chinese). Keep messages concise and focused.
- PRs should include: a clear description, linked issues (if any), and screenshots/GIFs for UI changes.

## Security & Configuration Tips
- Python dependencies are managed in `pyapp/requirements.txt`; frontend dependencies are in `gui/package.json`.
- OS-specific build steps use platform tools (Inno Setup, dmgbuild, dpkg); follow the scripts instead of ad-hoc commands.
