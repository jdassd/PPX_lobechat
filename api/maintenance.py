#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backup, restore staging and privacy-safe diagnostic bundles."""

from __future__ import annotations

import json
import os
import platform
import shutil
import sys
import tempfile
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict

from api.utils.error_handler import api_error, api_success
from pyapp.config.config import Config

_BACKUP_MANIFEST = "PPX_BACKUP_MANIFEST.json"
_FRONTEND_STATE = "frontend_state.json"
_EXCLUDED_ROOTS = {"backups", "restore"}


class MaintenanceMixin:
    """Cross-platform maintenance APIs for the desktop application."""

    @staticmethod
    def _maintenance_safe_frontend_state(value: Any) -> Dict[str, str]:
        if not isinstance(value, dict):
            return {}
        output = {}
        for key, item in value.items():
            key = str(key)
            if key.startswith("ppx-") and isinstance(item, str) and len(item) <= 1_000_000:
                output[key] = item
        return output

    @staticmethod
    def _maintenance_backup_path(output_dir: str = "", marker: str = "backup") -> Path:
        directory = Path(str(output_dir)).expanduser().resolve() if output_dir else Path(Config.appDataDir) / "backups"
        directory.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        target = directory / f'PPX_{marker}_{Config.appVersion.lstrip("v")}_{timestamp}.zip'
        index = 2
        while target.exists() or target.is_symlink():
            target = directory / f'PPX_{marker}_{Config.appVersion.lstrip("v")}_{timestamp}_{index}.zip'
            index += 1
        return target

    @staticmethod
    def _maintenance_is_excluded(relative: Path) -> bool:
        return bool(relative.parts and relative.parts[0] in _EXCLUDED_ROOTS)

    def maintenance_backup_create(self, options: Dict | None = None):
        try:
            options = options or {}
            app_data = Path(Config.appDataDir).resolve()
            marker = "before_restore" if options.get("_marker") == "before_restore" else "backup"
            target = self._maintenance_backup_path(str(options.get("outputDir") or ""), marker)
            frontend_state = self._maintenance_safe_frontend_state(options.get("frontendState"))
            files = []
            total_bytes = 0
            with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                for path in app_data.rglob("*"):
                    if not path.is_file() or path.is_symlink():
                        continue
                    relative = path.relative_to(app_data)
                    if self._maintenance_is_excluded(relative):
                        continue
                    try:
                        if path.resolve() == target.resolve():
                            continue
                        archive.write(path, f"data/{relative.as_posix()}")
                        size = path.stat().st_size
                        files.append({"path": relative.as_posix(), "size": size})
                        total_bytes += size
                    except OSError:
                        continue
                archive.writestr(_FRONTEND_STATE, json.dumps(frontend_state, ensure_ascii=False, indent=2))
                manifest = {
                    "schemaVersion": 1,
                    "appVersion": Config.appVersion,
                    "createdAt": time.time(),
                    "platform": Config.appSystem,
                    "fileCount": len(files),
                    "totalBytes": total_bytes,
                    "files": files,
                }
                archive.writestr(_BACKUP_MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2))
            return api_success("备份已创建", output=str(target), manifest=manifest)
        except Exception as exc:
            return api_error(f"创建备份失败：{exc}")

    @staticmethod
    def _maintenance_validate_backup(path: Path):
        if not path.is_file() or path.suffix.lower() != ".zip":
            raise ValueError("请选择 PPX 备份 ZIP 文件")
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if _BACKUP_MANIFEST not in names:
                raise ValueError("不是有效的 PPX 备份文件")
            for name in names:
                member = Path(name)
                if member.is_absolute() or ".." in member.parts:
                    raise ValueError("备份包含不安全路径")
            manifest = json.loads(archive.read(_BACKUP_MANIFEST).decode("utf-8"))
            try:
                frontend_state = (
                    json.loads(archive.read(_FRONTEND_STATE).decode("utf-8")) if _FRONTEND_STATE in names else {}
                )
            except (ValueError, UnicodeDecodeError):
                frontend_state = {}
        return manifest, MaintenanceMixin._maintenance_safe_frontend_state(frontend_state)

    def maintenance_backup_inspect(self, options: Dict | str | None = None):
        try:
            raw = options.get("filePath") if isinstance(options, dict) else options
            path = Path(str(raw or "")).expanduser().resolve()
            manifest, frontend_state = self._maintenance_validate_backup(path)
            return api_success("备份校验通过", manifest=manifest, frontendState=frontend_state, path=str(path))
        except Exception as exc:
            return api_error(f"校验备份失败：{exc}")

    def maintenance_backup_restore(self, options: Dict | None = None):
        """Stage a validated archive; it is applied before services start on next launch."""
        try:
            options = options or {}
            source = Path(str(options.get("filePath") or "")).expanduser().resolve()
            manifest, frontend_state = self._maintenance_validate_backup(source)
            restore_dir = Path(Config.appDataDir) / "restore"
            restore_dir.mkdir(parents=True, exist_ok=True)
            pending_archive = restore_dir / "pending.zip"
            temp_archive = restore_dir / f"pending-{uuid.uuid4().hex}.tmp"
            shutil.copy2(source, temp_archive)
            os.replace(temp_archive, pending_archive)
            marker = {
                "schemaVersion": 1,
                "archive": str(pending_archive),
                "requestedAt": time.time(),
                "source": str(source),
            }
            marker_path = restore_dir / "pending.json"
            temp_marker = restore_dir / f"pending-{uuid.uuid4().hex}.json.tmp"
            temp_marker.write_text(json.dumps(marker, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temp_marker, marker_path)
            return api_success(
                "恢复已安排，将在下次启动时应用",
                requiresRestart=True,
                manifest=manifest,
                frontendState=frontend_state,
            )
        except Exception as exc:
            return api_error(f"安排恢复失败：{exc}")

    def maintenance_apply_pending_restore(self):
        try:
            app_data = Path(Config.appDataDir).resolve()
            restore_dir = app_data / "restore"
            marker_path = restore_dir / "pending.json"
            if not marker_path.is_file():
                return api_success("没有待应用的恢复", restored=False)
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
            archive_path = Path(str(marker.get("archive") or "")).resolve()
            manifest, _ = self._maintenance_validate_backup(archive_path)
            recovery_dir = Path(Config.appDataDir) / "backups"
            backup_result = self.maintenance_backup_create(
                {"outputDir": str(recovery_dir), "_marker": "before_restore"}
            )
            if not (isinstance(backup_result, dict) and backup_result.get("code") == 0):
                raise RuntimeError("无法创建恢复前安全备份")
            with tempfile.TemporaryDirectory(prefix="ppx-restore-", dir=str(restore_dir)) as temp_dir:
                staging = Path(temp_dir)
                with zipfile.ZipFile(archive_path) as archive:
                    for info in archive.infolist():
                        if not info.filename.startswith("data/") or info.is_dir():
                            continue
                        relative = Path(info.filename).relative_to("data")
                        if relative.is_absolute() or ".." in relative.parts or self._maintenance_is_excluded(relative):
                            continue
                        staged = staging / relative
                        staged.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(info) as source_handle, staged.open("wb") as target_handle:
                            shutil.copyfileobj(source_handle, target_handle)
                for staged in staging.rglob("*"):
                    if not staged.is_file():
                        continue
                    relative = staged.relative_to(staging)
                    destination = app_data / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    temp_destination = destination.with_name(f"{destination.name}.{uuid.uuid4().hex}.restore")
                    shutil.copy2(staged, temp_destination)
                    os.replace(temp_destination, destination)
            marker_path.unlink(missing_ok=True)
            archive_path.unlink(missing_ok=True)
            return api_success(
                "备份恢复完成", restored=True, manifest=manifest, recoveryBackup=backup_result.get("output")
            )
        except Exception as exc:
            return api_error(f"应用待恢复备份失败：{exc}", restored=False)

    def maintenance_health(self):
        try:
            app_data = Path(Config.appDataDir)
            usage = shutil.disk_usage(app_data)
            capabilities = self.capabilities_get() if callable(getattr(self, "capabilities_get", None)) else {}
            checks = [
                {
                    "id": "app-data",
                    "name": "用户数据目录",
                    "ok": app_data.is_dir() and os.access(app_data, os.W_OK),
                    "detail": str(app_data),
                },
                {
                    "id": "disk",
                    "name": "可用磁盘空间",
                    "ok": usage.free >= 512 * 1024 * 1024,
                    "detail": f"{usage.free} bytes free",
                },
                {
                    "id": "python",
                    "name": "Python 运行时",
                    "ok": sys.version_info >= (3, 10),
                    "detail": platform.python_version(),
                },
            ]
            capability_values = capabilities.get("capabilities", {}) if isinstance(capabilities, dict) else {}
            for item in capability_values.values():
                checks.append(
                    {
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "ok": bool(item.get("available")),
                        "detail": item.get("detail"),
                    }
                )
            return api_success(
                "健康检查完成",
                healthy=all(item["ok"] for item in checks[:3]),
                checks=checks,
                appVersion=Config.appVersion,
                platform=Config.appSystem,
            )
        except Exception as exc:
            return api_error(f"健康检查失败：{exc}")

    def maintenance_diagnostics(self, options: Dict | None = None):
        try:
            options = options or {}
            output_dir_raw = options.get("outputDir")
            output_dir = (
                Path(str(output_dir_raw)).expanduser()
                if output_dir_raw
                else Path(Config.downloadDir or Config.appDataDir)
            )
            output_dir.mkdir(parents=True, exist_ok=True)
            target = output_dir / f'PPX_diagnostics_{time.strftime("%Y%m%d_%H%M%S")}.json'
            index = 2
            while target.exists() or target.is_symlink():
                target = output_dir / f'PPX_diagnostics_{time.strftime("%Y%m%d_%H%M%S")}_{index}.json'
                index += 1
            health = self.maintenance_health()
            task_summary = []
            if callable(getattr(self, "task_list", None)):
                task_response = self.task_list({"limit": 20})
                for item in task_response.get("tasks", []) if isinstance(task_response, dict) else []:
                    task_summary.append(
                        {key: item.get(key) for key in ("id", "method", "status", "message", "createdAt", "endedAt")}
                    )
            workflow_summary = []
            if callable(getattr(self, "workflow_list", None)):
                workflow_response = self.workflow_list()
                for item in workflow_response.get("runs", [])[:20] if isinstance(workflow_response, dict) else []:
                    workflow_summary.append(
                        {
                            key: item.get(key)
                            for key in ("id", "workflowId", "workflowName", "trigger", "status", "startedAt", "endedAt")
                        }
                    )
            payload = {
                "schemaVersion": 1,
                "createdAt": time.time(),
                "application": {"name": Config.appName, "version": Config.appVersion, "platform": Config.appSystem},
                "runtime": {
                    "python": platform.python_version(),
                    "implementation": platform.python_implementation(),
                    "architecture": platform.machine(),
                },
                "system": {"platform": platform.platform(), "release": platform.release()},
                "paths": {"appDataDir": Config.appDataDir, "codeDir": Config.codeDir},
                "health": health,
                "recentTasks": task_summary,
                "recentWorkflowRuns": workflow_summary,
                "privacy": "未收集环境变量、文件正文、任务参数、密码或访问令牌。",
            }
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return api_success("诊断报告已生成", output=str(target), report=payload)
        except Exception as exc:
            return api_error(f"生成诊断报告失败：{exc}")
