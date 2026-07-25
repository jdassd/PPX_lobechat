#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频处理相关 API
"""
from __future__ import annotations

import base64
import json
import mimetypes
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict

from api.utils import (
    api_error,
    api_success,
    ensure_file_path,
    ensure_files_payload,
    normalize_suffix,
    parse_timespan,
)


class VideoTool:
    """视频工具"""

    def _validate(self, options: Dict | None) -> Dict:
        if options is None:
            return {}
        if not isinstance(options, dict):
            raise ValueError('参数格式错误')
        return options

    def _require_ffmpeg(self) -> str:
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            raise OSError('未检测到 FFmpeg，请先安装或在系统 PATH 中配置')
        return ffmpeg

    def _require_ffprobe(self) -> str:
        ffprobe = shutil.which('ffprobe')
        if not ffprobe:
            raise OSError('未检测到 ffprobe，请安装完整 FFmpeg')
        return ffprobe

    def video_checkEnvironment(self):
        """启动操作前检查 FFmpeg 工具链，供界面给出可执行的安装提示。"""
        ffmpeg = shutil.which('ffmpeg')
        ffprobe = shutil.which('ffprobe')
        if not ffmpeg or not ffprobe:
            missing = [name for name, path in (('ffmpeg', ffmpeg), ('ffprobe', ffprobe)) if not path]
            return api_error(f'视频功能缺少运行环境：{", ".join(missing)}', available=False, missing=missing)
        return api_success('FFmpeg 环境已就绪', available=True, ffmpegPath=ffmpeg, ffprobePath=ffprobe)

    def _run(self, args):
        process = subprocess.run(args, capture_output=True, text=True)
        if process.returncode != 0:
            stderr = process.stderr.strip() or 'FFmpeg 执行失败'
            raise RuntimeError(stderr)

    def _probe_duration(self, file_path: Path) -> float:
        try:
            ffprobe = self._require_ffprobe()
        except OSError:
            return 0.0
        cmd = [
            ffprobe,
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(file_path),
        ]
        process = subprocess.run(cmd, capture_output=True, text=True)
        if process.returncode != 0:
            return 0.0
        try:
            return float(process.stdout.strip())
        except (TypeError, ValueError):
            return 0.0

    def _prepare_output(self, source: Path, options: Dict, suffix: str, extension: str | None = None) -> Path:
        output_dir = options.get('outputDir')
        if output_dir:
            dest_dir = Path(output_dir)
            dest_dir.mkdir(parents=True, exist_ok=True)
        else:
            dest_dir = source.parent / suffix
            dest_dir.mkdir(parents=True, exist_ok=True)
        filename = options.get('outputName') or f'{source.stem}_{suffix}'
        if extension:
            filename = normalize_suffix(filename, extension)
        return dest_dir / filename

    def _prepare_sequence_dir(self, source: Path, options: Dict, suffix: str) -> Path:
        output_dir = options.get('outputDir')
        if output_dir:
            base_dir = Path(output_dir)
            base_dir.mkdir(parents=True, exist_ok=True)
        else:
            base_dir = source.parent / suffix
            base_dir.mkdir(parents=True, exist_ok=True)
        target = base_dir / f'{source.stem}_{int(time.time())}'
        target.mkdir(parents=True, exist_ok=True)
        return target

    def video_preview(self, options: Dict | None = None):
        """视频预览：将小文件转为 data URL，避免前端直接访问 file:///"""
        try:
            opts = self._validate(options)
            # 支持 filePath / file / path 三种字段名
            file_opt = opts.get('filePath') or opts.get('file') or opts.get('path')
            source = ensure_file_path(file_opt)

            try:
                max_bytes = int(opts.get('maxBytes') or 16 * 1024 * 1024)
            except (TypeError, ValueError):
                max_bytes = 16 * 1024 * 1024
            max_bytes = max(1 * 1024 * 1024, min(max_bytes, 64 * 1024 * 1024))

            file_size = source.stat().st_size
            if file_size > max_bytes:
                return api_error('视频文件过大，暂不支持内嵌预览，请通过系统默认的视频播放器查看。')

            mime, _ = mimetypes.guess_type(source.name)
            if not mime or not mime.startswith('video/'):
                mime = 'video/mp4'

            data = source.read_bytes()
            encoded = base64.b64encode(data).decode('ascii')
            url = f'data:{mime};base64,{encoded}'
            return api_success('视频预览生成成功', preview=url, size=len(data))
        except Exception as exc:
            return api_error(f'视频预览失败：{exc}')

    # -------------------- P0 功能 --------------------

    def video_format_convert(self, options: Dict | None = None):
        """视频格式转换"""
        try:
            opts = self._validate(options)
            source = ensure_file_path(opts.get('filePath'))
            ffmpeg = self._require_ffmpeg()
            target_format = str(opts.get('targetFormat', 'mp4')).lstrip('.').lower() or 'mp4'
            quality_preset = str(opts.get('qualityPreset', 'medium')).lower()
            dest = self._prepare_output(source, opts, 'convert', target_format)

            # 原画模式：尽可能不重新编码，直接复制音视频流
            if quality_preset in {'origin', 'original', 'source', 'copy'}:
                args = [
                    ffmpeg,
                    '-y',
                    '-i', str(source),
                    '-c', 'copy',
                    str(dest),
                ]
            else:
                crf_map = {'high': 18, 'medium': 22, 'low': 28}
                crf = crf_map.get(quality_preset, 22)
                vcodec = opts.get('videoCodec') or 'libx264'
                acodec = opts.get('audioCodec') or 'aac'
                preset = str(opts.get('preset', 'medium') or 'medium')
                args = [
                    ffmpeg,
                    '-y',
                    '-i', str(source),
                    '-c:v', vcodec,
                    '-preset', preset,
                    '-crf', str(crf),
                    '-c:a', acodec,
                    str(dest),
                ]
            self._run(args)
            return api_success('格式转换完成', file=str(dest))
        except Exception as exc:
            return api_error(f'格式转换失败：{exc}')

    def video_compress(self, options: Dict | None = None):
        """视频压缩"""
        try:
            opts = self._validate(options)
            source = ensure_file_path(opts.get('filePath'))
            ffmpeg = self._require_ffmpeg()
            mode = opts.get('mode', 'preset')
            dest = self._prepare_output(source, opts, 'compress', source.suffix or '.mp4')
            args = [ffmpeg, '-y', '-i', str(source)]

            if mode == 'bitrate':
                bitrate = opts.get('bitrate') or '1500k'
                args += ['-b:v', bitrate, '-bufsize', bitrate, '-maxrate', bitrate, '-c:a', 'aac']
            elif mode == 'size':
                target_mb = float(opts.get('targetSizeMB') or 20)
                duration = self._probe_duration(source)
                if duration <= 0:
                    duration = 60.0
                bitrate_kbps = max(200, int((target_mb * 8192) / duration))
                bitrate = f'{bitrate_kbps}k'
                args += ['-b:v', bitrate, '-bufsize', bitrate, '-maxrate', bitrate, '-c:a', 'aac']
            else:
                preset = str(opts.get('preset', 'balanced')).lower()
                crf_map = {'high': 20, 'balanced': 24, 'small': 30}
                crf = crf_map.get(preset, 24)
                args += ['-c:v', 'libx264', '-preset', opts.get('ffPreset', 'medium'), '-crf', str(crf), '-c:a', 'aac']

            args.append(str(dest))
            self._run(args)
            return api_success('压缩完成', file=str(dest))
        except Exception as exc:
            return api_error(f'压缩失败：{exc}')

    def video_cut(self, options: Dict | None = None):
        """视频截取"""
        try:
            opts = self._validate(options)
            source = ensure_file_path(opts.get('filePath'))
            ffmpeg = self._require_ffmpeg()
            start_seconds, start_label = parse_timespan(opts.get('start') or 0)
            end_seconds, end_label = parse_timespan(opts.get('end') or 0)
            if end_seconds and end_seconds <= start_seconds:
                raise ValueError('结束时间必须大于开始时间')
            dest = self._prepare_output(source, opts, 'clip', source.suffix or '.mp4')
            args = [
                ffmpeg,
                '-y',
                '-ss', start_label,
                '-i', str(source),
            ]
            if end_seconds:
                duration = end_seconds - start_seconds
                _, duration_label = parse_timespan(duration)
                args += ['-t', duration_label]
            args += ['-c', 'copy', str(dest)]
            self._run(args)
            return api_success('截取完成', file=str(dest))
        except Exception as exc:
            return api_error(f'截取失败：{exc}')

    def video_extract_audio(self, options: Dict | None = None):
        """提取音频"""
        try:
            opts = self._validate(options)
            source = ensure_file_path(opts.get('filePath'))
            ffmpeg = self._require_ffmpeg()
            audio_format = str(opts.get('audioFormat', 'mp3')).lower()
            quality = str(opts.get('quality', 'medium')).lower()
            start_seconds, start_label = parse_timespan(opts.get('start') or 0)
            end_seconds, end_label = parse_timespan(opts.get('end') or 0)
            if end_seconds and end_seconds <= start_seconds:
                raise ValueError('结束时间必须大于开始时间')
            bitrate_map = {'high': '320k', 'medium': '192k', 'low': '128k'}
            codec_args = {
                'mp3': ['-c:a', 'libmp3lame'],
                'aac': ['-c:a', 'aac'],
                'wav': ['-c:a', 'pcm_s16le'],
                'flac': ['-c:a', 'flac'],
            }
            dest = self._prepare_output(source, opts, 'audio', audio_format)
            args = [ffmpeg, '-y', '-ss', start_label, '-i', str(source), '-vn']
            if end_seconds:
                duration = end_seconds - start_seconds
                _, duration_label = parse_timespan(duration)
                args += ['-t', duration_label]
            args += codec_args.get(audio_format, ['-c:a', 'aac'])
            if audio_format not in {'wav'}:
                args += ['-b:a', bitrate_map.get(quality, '192k')]
            args.append(str(dest))
            self._run(args)
            return api_success('音频提取完成', file=str(dest))
        except Exception as exc:
            return api_error(f'音频提取失败：{exc}')

    def video_concat(self, options: Dict | None = None):
        """多视频合成"""
        try:
            opts = self._validate(options)
            raw_files = opts.get('files') or opts.get('fileList')
            if not raw_files:
                raise ValueError('请至少选择 2 个视频文件')
            files = ensure_files_payload({'files': raw_files})
            if len(files) < 2:
                raise ValueError('至少需要两个视频文件')
            ffmpeg = self._require_ffmpeg()
            reencode = bool(opts.get('reencode', False))
            base = files[0]
            target_format = str(opts.get('targetFormat') or base.suffix or '.mp4').lstrip('.')
            dest = self._prepare_output(base, opts, 'concat', target_format)
            manifest = dest.with_suffix('.concat.txt')
            try:
                with manifest.open('w', encoding='utf-8') as handler:
                    for path in files:
                        normalized = str(path).replace('\\', '/').replace("'", r"'\''")
                        handler.write(f"file '{normalized}'\n")
                args = [
                    ffmpeg,
                    '-y',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', str(manifest),
                ]
                if reencode:
                    vcodec = opts.get('videoCodec') or 'libx264'
                    acodec = opts.get('audioCodec') or 'aac'
                    crf = opts.get('crf')
                    try:
                        crf_value = int(crf) if crf is not None else 22
                    except (TypeError, ValueError):
                        crf_value = 22
                    preset = opts.get('preset', 'medium')
                    args += ['-c:v', vcodec, '-preset', preset, '-crf', str(crf_value), '-c:a', acodec]
                else:
                    args += ['-c', 'copy']
                args.append(str(dest))
                self._run(args)
            finally:
                if manifest.exists():
                    manifest.unlink()
            return api_success('视频合成完成', file=str(dest))
        except Exception as exc:
            return api_error(f'视频合成失败：{exc}')
