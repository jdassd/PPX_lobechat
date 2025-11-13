#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频处理相关 API
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict

from api.utils import (
    api_error,
    api_success,
    ensure_file_path,
    parse_timespan,
    normalize_suffix,
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
            raise EnvironmentError('未检测到 FFmpeg，请先安装或在系统 PATH 中配置')
        return ffmpeg

    def _require_ffprobe(self) -> str:
        ffprobe = shutil.which('ffprobe')
        if not ffprobe:
            raise EnvironmentError('未检测到 ffprobe，请安装完整 FFmpeg')
        return ffprobe

    def _run(self, args):
        process = subprocess.run(args, capture_output=True, text=True)
        if process.returncode != 0:
            stderr = process.stderr.strip() or 'FFmpeg 执行失败'
            raise RuntimeError(stderr)

    def _probe_duration(self, file_path: Path) -> float:
        try:
            ffprobe = self._require_ffprobe()
        except EnvironmentError:
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

    # -------------------- P0 功能 --------------------

    def video_format_convert(self, options: Dict | None = None):
        """视频格式转换"""
        try:
            opts = self._validate(options)
            source = ensure_file_path(opts.get('filePath'))
            ffmpeg = self._require_ffmpeg()
            target_format = str(opts.get('targetFormat', 'mp4')).lstrip('.').lower() or 'mp4'
            quality_preset = str(opts.get('qualityPreset', 'medium')).lower()
            crf_map = {'high': 18, 'medium': 22, 'low': 28}
            crf = crf_map.get(quality_preset, 22)
            vcodec = opts.get('videoCodec') or 'libx264'
            acodec = opts.get('audioCodec') or 'aac'
            dest = self._prepare_output(source, opts, 'convert', target_format)
            args = [
                ffmpeg,
                '-y',
                '-i', str(source),
                '-c:v', vcodec,
                '-preset', opts.get('preset', 'medium'),
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
            bitrate_map = {'high': '320k', 'medium': '192k', 'low': '128k'}
            codec_args = {
                'mp3': ['-c:a', 'libmp3lame'],
                'aac': ['-c:a', 'aac'],
                'wav': ['-c:a', 'pcm_s16le'],
                'flac': ['-c:a', 'flac'],
            }
            dest = self._prepare_output(source, opts, 'audio', audio_format)
            args = [ffmpeg, '-y', '-i', str(source), '-vn']
            args += codec_args.get(audio_format, ['-c:a', 'aac'])
            if audio_format not in {'wav'}:
                args += ['-b:a', bitrate_map.get(quality, '192k')]
            args.append(str(dest))
            self._run(args)
            return api_success('音频提取完成', file=str(dest))
        except Exception as exc:
            return api_error(f'音频提取失败：{exc}')

    def video_extract_frames(self, options: Dict | None = None):
        """提取帧图"""
        try:
            opts = self._validate(options)
            source = ensure_file_path(opts.get('filePath'))
            ffmpeg = self._require_ffmpeg()
            mode = str(opts.get('mode', 'time')).lower()
            interval = max(1, int(opts.get('interval') or 5))
            image_format = str(opts.get('imageFormat', 'png')).lower()
            dest_dir = self._prepare_sequence_dir(source, opts, 'frames')
            pattern = dest_dir / f'{source.stem}_%04d.{image_format}'
            args = [ffmpeg, '-y', '-i', str(source)]
            if mode == 'frame':
                args += ['-vf', f"select='not(mod(n\\,{interval}))'", '-vsync', 'vfr']
            else:
                fps_expr = f'1/{interval}' if interval else '1'
                args += ['-vf', f'fps={fps_expr}']
            args.append(str(pattern))
            self._run(args)
            files = sorted(dest_dir.glob(f'{source.stem}_*.{image_format}'))
            preview = [str(path) for path in files[:10]]
            return api_success('帧图提取完成', outputDir=str(dest_dir), files=preview, count=len(files))
        except Exception as exc:
            return api_error(f'帧图提取失败：{exc}')

    def video_get_info(self, options: Dict | None = None):
        """获取视频信息"""
        try:
            opts = self._validate(options)
            source = ensure_file_path(opts.get('filePath'))
            ffprobe = self._require_ffprobe()
            cmd = [
                ffprobe,
                '-v', 'error',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(source),
            ]
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.returncode != 0:
                raise RuntimeError(process.stderr.strip() or '无法解析视频信息')
            payload = json.loads(process.stdout or '{}')
            video_stream = next((stream for stream in payload.get('streams', []) if stream.get('codec_type') == 'video'), {})
            audio_stream = next((stream for stream in payload.get('streams', []) if stream.get('codec_type') == 'audio'), {})
            info = {
                'duration': float(payload.get('format', {}).get('duration') or 0),
                'bitrate': payload.get('format', {}).get('bit_rate'),
                'size': payload.get('format', {}).get('size'),
                'videoCodec': video_stream.get('codec_name'),
                'audioCodec': audio_stream.get('codec_name'),
                'width': video_stream.get('width'),
                'height': video_stream.get('height'),
                'fps': video_stream.get('avg_frame_rate'),
            }
            return api_success('视频信息获取完成', info=info, raw=payload)
        except Exception as exc:
            return api_error(f'读取视频信息失败：{exc}')
