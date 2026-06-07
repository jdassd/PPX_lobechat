#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Codex
Date: 2026-06-07
Description: Word(.docx) 工具相关 API —— 切割与合并
'''

import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

from docx import Document
from docx.oxml.ns import qn
from docxcompose.composer import Composer

from api.utils.validators import ensure_output_directory


class WordTool():
    '''Word(.docx) 相关功能：切割、合并'''

    def _ensure_word_file(self, file_path: str) -> Path:
        if not file_path:
            raise ValueError('请选择 Word 文件')
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f'文件不存在：{path}')
        if path.suffix.lower() == '.doc':
            raise ValueError('暂不支持旧版 .doc 格式，请先另存为 .docx')
        if path.suffix.lower() != '.docx':
            raise ValueError('仅支持 .docx 文件')
        return path

    def _timestamp(self) -> str:
        return datetime.now().strftime('%Y%m%d_%H%M%S')

    def _compose_output_path(self, directory: str, filename: str) -> str:
        if directory and filename:
            safe_dir = Path(directory)
            safe_dir.mkdir(parents=True, exist_ok=True)
            safe_name = filename if filename.lower().endswith('.docx') else f'{filename}.docx'
            return str(safe_dir / safe_name)
        return ''

    def _resolve_output_path(self, source: Path, output_path: str, suffix: str) -> Path:
        if output_path:
            dest = Path(output_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
        else:
            dest = source.parent / f'{source.stem}_{suffix}_{self._timestamp()}.docx'
        return dest

    # --- 文档结构辅助 -------------------------------------------------

    def _content_blocks(self, document: Document) -> List:
        '''按文档顺序返回正文中的段落(w:p)与表格(w:tbl)元素，忽略结尾的 sectPr。'''
        blocks = []
        for child in document.element.body.iterchildren():
            if child.tag in (qn('w:p'), qn('w:tbl')):
                blocks.append(child)
        return blocks

    def _has_page_break(self, paragraph_el) -> bool:
        '''段落是否包含手动分页符（run 级 <w:br w:type="page"/>）。'''
        for br in paragraph_el.iter(qn('w:br')):
            if br.get(qn('w:type')) == 'page':
                return True
        return False

    def _has_section_break(self, paragraph_el) -> bool:
        '''段落是否为分节符（pPr 内嵌 sectPr，意味着下一段开始新节/新页）。'''
        pPr = paragraph_el.find(qn('w:pPr'))
        if pPr is not None and pPr.find(qn('w:sectPr')) is not None:
            return True
        return False

    def _style_id_of(self, paragraph_el) -> str:
        pPr = paragraph_el.find(qn('w:pPr'))
        if pPr is None:
            return ''
        pStyle = pPr.find(qn('w:pStyle'))
        if pStyle is None:
            return ''
        return pStyle.get(qn('w:val')) or ''

    def _is_heading(self, paragraph_el, id_to_name: Dict[str, str], level: int) -> bool:
        if paragraph_el.tag != qn('w:p'):
            return False
        style_id = self._style_id_of(paragraph_el)
        if not style_id:
            return False
        name = (id_to_name.get(style_id) or '').strip().lower()
        sid = style_id.strip().lower()
        if name in {f'heading {level}', f'标题 {level}'}:
            return True
        if sid == f'heading{level}':
            return True
        return False

    def _segments_by_count(self, total: int, per_file: int) -> List[range]:
        per_file = max(1, per_file)
        return [range(start, min(start + per_file, total)) for start in range(0, total, per_file)]

    def _segments_by_boundaries(self, total: int, boundaries: List[int]) -> List[range]:
        '''根据切点(每段起始下标)生成连续区间。'''
        points = sorted({b for b in boundaries if 0 <= b < total})
        if not points or points[0] != 0:
            points = [0] + points
        segments: List[range] = []
        for idx, start in enumerate(points):
            end = points[idx + 1] if idx + 1 < len(points) else total
            if start < end:
                segments.append(range(start, end))
        return segments

    def _write_segment(self, source: Path, dest: Path, keep_indices) -> None:
        '''复制源文件后裁剪正文，仅保留指定下标的内容块，最大限度保留样式/图片/页眉页脚。'''
        shutil.copyfile(source, dest)
        doc = Document(str(dest))
        blocks = self._content_blocks(doc)
        keep = set(keep_indices)
        body = doc.element.body
        for index, block in enumerate(blocks):
            if index not in keep:
                body.remove(block)
        doc.save(str(dest))

    # --- 对外 API ----------------------------------------------------

    def word_split(self, options: Dict = None):
        '''Word 文档切割为多个 .docx

        支持三种模式（mode）：
          - paragraphs : 每 N 个内容块（段落/表格）切一个文件（默认）
          - pagebreak  : 在手动分页符 / 分节符处切割
          - heading    : 在指定级别的标题处切割
        '''
        try:
            opts = options if isinstance(options, dict) else {}
            source = self._ensure_word_file(opts.get('filePath', ''))
            mode = str(opts.get('mode') or 'paragraphs').lower()
            per_file = int(opts.get('paragraphsPerFile') or 10)
            heading_level = int(opts.get('headingLevel') or 1)

            output_dir_opt = opts.get('outputDir', '')
            out_dir = ensure_output_directory(source, output_dir_opt, 'split')

            doc = Document(str(source))
            blocks = self._content_blocks(doc)
            total = len(blocks)
            if total == 0:
                raise ValueError('文档没有可切割的内容')

            if mode == 'paragraphs':
                segments = self._segments_by_count(total, per_file)
            elif mode == 'pagebreak':
                boundaries: List[int] = []
                for index, block in enumerate(blocks):
                    if block.tag != qn('w:p'):
                        continue
                    if self._has_page_break(block) and index != 0:
                        boundaries.append(index)
                    if self._has_section_break(block) and index + 1 < total:
                        boundaries.append(index + 1)
                segments = self._segments_by_boundaries(total, boundaries)
                if len(segments) <= 1:
                    raise ValueError('未检测到分页符/分节符，无法按分页切割')
            elif mode == 'heading':
                id_to_name = {}
                try:
                    id_to_name = {s.style_id: s.name for s in doc.styles}
                except Exception:
                    id_to_name = {}
                boundaries = [
                    index for index, block in enumerate(blocks)
                    if self._is_heading(block, id_to_name, heading_level)
                ]
                segments = self._segments_by_boundaries(total, boundaries)
                if len(segments) <= 1:
                    raise ValueError(f'未检测到 {heading_level} 级标题，无法按标题切割')
            else:
                raise ValueError('未知的切割模式')

            if len(segments) > 500:
                raise ValueError('切割份数过多（>500），请调整参数')

            base_name = opts.get('outputName') or source.stem
            if base_name.lower().endswith('.docx'):
                base_name = base_name[:-5]

            exported: List[str] = []
            for part, segment in enumerate(segments, start=1):
                dest = out_dir / f'{base_name}_part{part:03}.docx'
                self._write_segment(source, dest, segment)
                exported.append(str(dest))

            return {
                'code': 0,
                'msg': f'切割完成，共 {len(exported)} 个文件',
                'files': exported,
                'outputDir': str(out_dir)
            }
        except Exception as exc:
            return {'code': -1, 'msg': f'切割失败：{exc}'}

    def word_merge(self, options: Dict = None):
        '''多个 Word(.docx) 合并为一个文档'''
        try:
            opts = options if isinstance(options, dict) else {}
            files = opts.get('files', [])
            if not isinstance(files, Iterable):
                raise ValueError('参数格式错误')
            page_break = bool(opts.get('pageBreak', True))

            paths: List[Path] = []
            for item in files:
                path = item.get('path', '') if isinstance(item, dict) else str(item)
                paths.append(self._ensure_word_file(path))

            if len(paths) < 2:
                raise ValueError('请至少选择 2 个 Word 文件')

            output_path = opts.get('outputPath') or self._compose_output_path(
                opts.get('outputDir', ''), opts.get('outputName', '')
            )
            dest = self._resolve_output_path(paths[0], output_path, 'merged')

            master = Document(str(paths[0]))
            composer = Composer(master)
            for extra in paths[1:]:
                if page_break:
                    master.add_page_break()
                composer.append(Document(str(extra)))
            composer.save(str(dest))

            return {
                'code': 0,
                'msg': f'合并成功，共 {len(paths)} 个文件',
                'output': str(dest)
            }
        except Exception as exc:
            return {'code': -1, 'msg': f'合并失败：{exc}'}
