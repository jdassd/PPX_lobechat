#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频处理相关 API
"""
from __future__ import annotations

import base64
import json
import mimetypes
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict

from api.core.context import checkpoint, report_progress, run_process, stop_process
from api.core.outputs import atomic_output
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

    def _run(self, args, duration_hint=None):
        requested = [args[index + 1] for index, value in enumerate(args[:-1]) if value in {'-c:v', '-c:a'} and args[index + 1] != 'copy']
        if requested:
            available = run_process([args[0], '-hide_banner', '-encoders'], text=True, timeout=15)
            encoders = {line.split()[1] for line in available.stdout.splitlines() if len(line.split()) > 1}
            missing = [encoder for encoder in requested if encoder not in encoders]
            if missing:
                raise ValueError('当前 FFmpeg 缺少编码器：' + ', '.join(missing))
        source = Path(args[args.index('-i') + 1]) if '-i' in args else None
        duration = self._probe_duration(source) if source and source.suffix != '.txt' else 0
        if duration_hint is not None:
            duration = duration_hint
        if '-t' in args:
            duration = parse_timespan(args[args.index('-t') + 1])[0]
        with atomic_output(Path(args[-1])) as (temporary, final):
            command = [*args[:-1], '-progress', 'pipe:1', '-nostats', str(temporary)]
            lines = queue.Queue()
            errors = []
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                       encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            def read_lines():
                for line in process.stdout:
                    lines.put(line.strip())
            def read_errors():
                for line in process.stderr:
                    errors.append(line.rstrip())
                    del errors[:-60]
            readers = [threading.Thread(target=read_lines, daemon=True), threading.Thread(target=read_errors, daemon=True)]
            for reader in readers:
                reader.start()
            started = time.monotonic()
            try:
                while process.poll() is None or not lines.empty():
                    checkpoint()
                    if time.monotonic() - started > 7200:
                        raise TimeoutError('视频处理超过两小时，请分段处理')
                    try:
                        line = lines.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    if line.startswith('out_time_us='):
                        try:
                            seconds = int(line.partition('=')[2]) / 1_000_000
                            report_progress(max(0, seconds), duration, f'已处理 {max(0, seconds):.1f} 秒' + (f' / {duration:.1f} 秒' if duration else ''))
                        except ValueError:
                            pass
                if process.wait() != 0:
                    raise RuntimeError('\n'.join(errors[-12:]) or 'FFmpeg 执行失败')
                checked = self._inspect(temporary)
                if not checked.get('streams'):
                    raise RuntimeError('FFmpeg 未生成有效媒体流')
            finally:
                if process.poll() is None:
                    stop_process(process)
                for reader in readers:
                    reader.join(timeout=1)
                process.stdout.close()
                process.stderr.close()
        return final

    def _inspect(self, source):
        process = run_process([self._require_ffprobe(), '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(source)],
                              capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
        if process.returncode:
            raise ValueError(process.stderr.strip() or '无法读取视频编码信息')
        return json.loads(process.stdout)

    def video_inspect(self, options=None):
        try:
            source = ensure_file_path((options or {}).get('filePath'))
            info = self._inspect(source)
            encoders = run_process([self._require_ffmpeg(), '-hide_banner', '-encoders'], capture_output=True, text=True, timeout=15)
            return api_success('媒体检查完成', streams=info.get('streams', []), format=info.get('format', {}),
                               encoders=[line.split()[1] for line in encoders.stdout.splitlines() if len(line.split()) > 1 and line.strip()[0:1] in {'V', 'A'}])
        except Exception as exc:
            return api_error(f'媒体检查失败：{exc}', errorCode='MEDIA_INSPECTION_FAILED')

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
        process = run_process(cmd, capture_output=True, text=True, timeout=30)
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
            original_duration = self._probe_duration(source)
            start = parse_timespan(opts.get('start') or 0)[0]
            preview_duration = max(1, min(30, float(opts.get('duration') or 15)))
            if file_size > max_bytes or opts.get('start') is not None or source.suffix.lower() not in {'.mp4', '.webm'}:
                if original_duration and start >= original_duration:
                    raise ValueError('预览起点超出视频时长')
                with tempfile.TemporaryDirectory(prefix='ppx-video-preview-') as temporary:
                    preview_path = self._run([self._require_ffmpeg(), '-y', '-ss', str(start), '-i', str(source), '-t', str(preview_duration),
                                              '-vf', 'scale=min(960\\,iw):-2', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
                                              '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', str(Path(temporary) / 'preview.mp4')])
                    data = preview_path.read_bytes()
                return api_success('片段预览已生成', preview='data:video/mp4;base64,' + base64.b64encode(data).decode('ascii'),
                                   size=len(data), duration=original_duration, previewStart=start, previewDuration=min(preview_duration, max(0, original_duration - start)), segment=True)

            mime, _ = mimetypes.guess_type(source.name)
            if not mime or not mime.startswith('video/'):
                mime = 'video/mp4'

            data = source.read_bytes()
            encoded = base64.b64encode(data).decode('ascii')
            url = f'data:{mime};base64,{encoded}'
            return api_success('视频预览生成成功', preview=url, size=len(data), duration=original_duration, previewStart=0, segment=False)
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
                vcodec = opts.get('videoCodec') or ('libvpx-vp9' if target_format == 'webm' else 'libx264')
                acodec = opts.get('audioCodec') or ('libopus' if target_format == 'webm' else 'aac')
                if target_format == 'webm' and (vcodec not in {'libvpx', 'libvpx-vp9', 'libaom-av1', 'libsvtav1'} or acodec not in {'libopus', 'libvorbis'}):
                    raise ValueError('WebM 需要 VP8/VP9/AV1 视频及 Opus/Vorbis 音频，请调整编码器')
                preset = str(opts.get('preset', 'medium') or 'medium')
                args = [
                    ffmpeg,
                    '-y',
                    '-i', str(source),
                    '-c:v', vcodec,
                    '-crf', str(crf),
                    '-c:a', acodec,
                    str(dest),
                ]
                if vcodec in {'libx264', 'libx265'}:
                    args[-1:-1] = ['-preset', preset]
            dest = self._run(args)
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
            dest = self._prepare_output(source, opts, 'compress', '.mp4')
            args = [ffmpeg, '-y', '-i', str(source)]

            if mode == 'bitrate':
                bitrate = opts.get('bitrate') or '1500k'
                args += ['-b:v', bitrate, '-bufsize', bitrate, '-maxrate', bitrate, '-c:a', 'aac']
            elif mode == 'size':
                target_mb = float(opts.get('targetSizeMB') or 20)
                duration = self._probe_duration(source)
                if duration <= 0:
                    raise ValueError('无法读取视频时长，不能按目标大小计算码率')
                bitrate_kbps = max(200, int((target_mb * 8192) / duration))
                bitrate = f'{bitrate_kbps}k'
                args += ['-b:v', bitrate, '-bufsize', bitrate, '-maxrate', bitrate, '-c:a', 'aac']
            else:
                preset = str(opts.get('preset', 'balanced')).lower()
                crf_map = {'high': 20, 'balanced': 24, 'small': 30}
                crf = crf_map.get(preset, 24)
                args += ['-c:v', 'libx264', '-preset', opts.get('ffPreset', 'medium'), '-crf', str(crf), '-c:a', 'aac']

            args.append(str(dest))
            dest = self._run(args)
            return api_success('压缩完成', file=str(dest))
        except Exception as exc:
            return api_error(f'压缩失败：{exc}')

    def video_cut(self, options: Dict | None = None):
        """视频截取"""
        try:
            opts = self._validate(options)
            source = ensure_file_path(opts.get('filePath'))
            ffmpeg = self._require_ffmpeg()
            start_seconds, _ = parse_timespan(opts.get('start') or 0)
            end_seconds, _ = parse_timespan(opts.get('end') or 0)
            if end_seconds and end_seconds <= start_seconds:
                raise ValueError('结束时间必须大于开始时间')
            source_duration = self._probe_duration(source)
            if source_duration > 0 and (start_seconds >= source_duration or end_seconds > source_duration + 0.1):
                raise ValueError('截取范围超出视频时长')
            dest = self._prepare_output(source, opts, 'clip', source.suffix if opts.get('fastCopy') else '.mp4')
            args = [
                ffmpeg,
                '-y',
                '-ss', str(start_seconds),
                '-i', str(source),
            ]
            if end_seconds:
                duration = end_seconds - start_seconds
                args += ['-t', str(duration)]
            args += (['-c', 'copy'] if opts.get('fastCopy') else ['-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-c:a', 'aac']) + [str(dest)]
            dest = self._run(args)
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
            dest = self._run(args)
            return api_success('音频提取完成', file=str(dest))
        except Exception as exc:
            return api_error(f'音频提取失败：{exc}')

    def _concat_sources(self, files):
        profiles = [self._inspect(path) for path in files]
        keys = ('codec_type', 'codec_name', 'profile', 'width', 'height', 'pix_fmt', 'r_frame_rate',
                'time_base', 'sample_rate', 'channels', 'channel_layout')
        signatures = [tuple(tuple(stream.get(key) for key in keys) for stream in info.get('streams', [])
                            if stream.get('codec_type') in {'video', 'audio'}) for info in profiles]
        if any(not any(stream.get('codec_type') == 'video' for stream in info.get('streams', [])) for info in profiles):
            raise ValueError('拼接输入必须包含视频画面')
        return profiles, all(signature == signatures[0] for signature in signatures)

    def video_concat_preview(self, options=None):
        try:
            files = ensure_files_payload({'files': (options or {}).get('files') or []})
            profiles, compatible = self._concat_sources(files)
            return api_success('可直接拼接' if compatible else '编码或画面参数不同，请开启重编码拼接',
                               compatible=compatible, files=[{'path': str(path), 'streams': info['streams']} for path, info in zip(files, profiles, strict=True)])
        except Exception as exc:
            return api_error(f'拼接检查失败：{exc}')

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
            profiles, compatible = self._concat_sources(files)
            if not reencode and not compatible:
                raise ValueError('输入视频的编码、尺寸、帧率或音轨不同，请开启重编码拼接')
            durations = [float(info.get('format', {}).get('duration') or 0) for info in profiles]
            base = files[0]
            target_format = str(opts.get('targetFormat') or base.suffix or '.mp4').lstrip('.')
            dest = self._prepare_output(base, opts, 'concat', target_format)
            with tempfile.NamedTemporaryFile(prefix='.ppx-concat-', suffix='.txt', dir=dest.parent, delete=False) as handle:
                manifest = Path(handle.name)
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
                    if any(duration <= 0 for duration in durations):
                        raise ValueError('无法确认全部输入的时长，请先修复或转换异常视频')
                    video = next(stream for stream in profiles[0]['streams'] if stream.get('codec_type') == 'video')
                    width, height = int(video['width']) // 2 * 2, int(video['height']) // 2 * 2
                    fps = video.get('avg_frame_rate') or video.get('r_frame_rate') or '30'
                    if fps in {'0/0', '0'}:
                        fps = '30'
                    audio = any(any(stream.get('codec_type') == 'audio' for stream in info['streams']) for info in profiles)
                    args = [ffmpeg, '-y']
                    filters, inputs = [], []
                    for index, path in enumerate(files):
                        args += ['-i', str(path)]
                        filters.append(f'[{index}:v:0]scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},setpts=PTS-STARTPTS[v{index}]')
                        inputs.append(f'[v{index}]')
                        if audio:
                            if any(stream.get('codec_type') == 'audio' for stream in profiles[index]['streams']):
                                filters.append(f'[{index}:a:0]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={durations[index]},asetpts=PTS-STARTPTS[a{index}]')
                            else:
                                filters.append(f'anullsrc=r=48000:cl=stereo,atrim=duration={durations[index]}[a{index}]')
                            inputs.append(f'[a{index}]')
                    filters.append(''.join(inputs) + f'concat=n={len(files)}:v=1:a={1 if audio else 0}[v]' + ('[a]' if audio else ''))
                    args += ['-filter_complex', ';'.join(filters), '-map', '[v]']
                    if audio:
                        args += ['-map', '[a]']
                    vcodec = opts.get('videoCodec') or ('libvpx-vp9' if target_format == 'webm' else 'libx264')
                    acodec = opts.get('audioCodec') or ('libopus' if target_format == 'webm' else 'aac')
                    crf = opts.get('crf')
                    try:
                        crf_value = int(crf) if crf is not None else 22
                    except (TypeError, ValueError):
                        crf_value = 22
                    preset = opts.get('preset', 'medium')
                    args += ['-c:v', vcodec, '-crf', str(crf_value), '-pix_fmt', 'yuv420p']
                    if vcodec in {'libx264', 'libx265'}:
                        args += ['-preset', preset]
                    if audio:
                        args += ['-c:a', acodec]
                else:
                    args += ['-c', 'copy']
                args.append(str(dest))
                dest = self._run(args, duration_hint=sum(durations))
            finally:
                if manifest.exists():
                    manifest.unlink()
            return api_success('视频合成完成', file=str(dest))
        except Exception as exc:
            return api_error(f'视频合成失败：{exc}')
