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
- `pnpm run test` runs Python unittest cases in `tests/`; `pnpm run test:gui` runs frontend contract checks.
- `pnpm run test:e2e` builds the frontend and verifies complete workflows with Playwright and the real Python API.
- Run checks appropriate to the change. Native installation, upgrade and restore acceptance is tracked separately in `docs/refactor-acceptance.json`.

## 后续产品方向
- 用户于 2026-09-09 明确要求：后续版本重点剔除没用的功能，增加实用功能。以减少实际操作和提高批处理可靠性为标准，不以功能数量为目标。
- 先合并重复入口、删除无调用或已被替代的实现，再扩展已有主流程；删除时保持旧工作流迁移和历史可读，不清除用户数据。
- 优先级和候选取舍见 `docs/toolbox-function-priorities.md`；整体契约见 `docs/toolbox-design.md`，实际发布状态见 `docs/toolbox-iterations.md`。

## Commit & Pull Request Guidelines
- Recent commits are short, imperative summaries (often in Chinese). Keep messages concise and focused.
- PRs should include: a clear description, linked issues (if any), and screenshots/GIFs for UI changes.

## Security & Configuration Tips
- Python dependencies are managed in `pyapp/requirements.txt`; frontend dependencies are in `gui/package.json`.
- OS-specific build steps use platform tools (Inno Setup, dmgbuild, dpkg); follow the scripts instead of ad-hoc commands.
