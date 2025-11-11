#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Codex
Date: 2025-11-11
Description: Excel 工具相关 API
'''

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from openpyxl import Workbook, load_workbook


class Excel():
    '''Excel 相关功能'''

    _supported_suffix = ('.xlsx', '.xlsm', '.xltx', '.xltm')

    # -------- helpers --------

    def _validate_payload(self, options: Optional[Dict]) -> Dict:
        if options is None:
            return {}
        if not isinstance(options, dict):
            raise ValueError('参数格式错误')
        return options

    def _ensure_excel_file(self, file_path: str) -> Path:
        if not file_path:
            raise ValueError('请选择 Excel 文件')
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f'文件不存在：{path}')
        if path.suffix.lower() not in self._supported_suffix:
            raise ValueError('仅支持 .xlsx / .xlsm / .xltx / .xltm 文件')
        return path

    def _load_sheet(self, file_path: Path, sheet_name: Optional[str]) -> Tuple[List[str], List[List[Any]], str]:
        wb = load_workbook(file_path, data_only=True)
        if sheet_name:
            if sheet_name not in wb.sheetnames:
                raise ValueError(f'工作表不存在：{sheet_name}')
            ws = wb[sheet_name]
        else:
            ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        wb.close()
        if not rows:
            return [], [], ws.title
        header = [self._normalize_cell(cell) for cell in rows[0]]
        data_rows: List[List[Any]] = []
        for row in rows[1:]:
            if row is None:
                continue
            if all(self._normalize_cell(cell) == '' for cell in row):
                continue
            data_rows.append(list(row))
        return header, data_rows, ws.title

    def _normalize_cell(self, value: Any) -> str:
        if value is None:
            return ''
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        return str(value).strip()

    def _normalize_schema(self, schema_text: str, delimiter: str, header: Sequence[str]) -> List[str]:
        if schema_text:
            chunks = [part.strip() for part in schema_text.split(delimiter or '|')]
            normalized = [chunk for chunk in chunks if chunk]
            if normalized:
                return normalized
        # Fallback to workbook header
        fallback = [col or f'列{i + 1}' for i, col in enumerate(header)]
        if not fallback:
            fallback = ['列1']
        return fallback

    def _rows_to_dicts(self, schema: Sequence[str], rows: Iterable[Sequence[Any]], source: str) -> List[Dict[str, Any]]:
        mapped: List[Dict[str, Any]] = []
        max_len = len(schema)
        for raw in rows:
            row_dict: Dict[str, Any] = {}
            for idx, key in enumerate(schema):
                value = raw[idx] if idx < len(raw) else None
                row_dict[key] = self._normalize_cell(value)
            row_dict['_source'] = source
            mapped.append(row_dict)
        return mapped

    def _ensure_output_dir(self, source: Path, preferred: str, suffix: str) -> Path:
        if preferred:
            output = Path(preferred)
        else:
            output = source.parent / f'{source.stem}_{suffix}'
        output.mkdir(parents=True, exist_ok=True)
        return output

    def _write_rows(self, schema: Sequence[str], rows: Iterable[Dict[str, Any]], dest: Path):
        wb = Workbook()
        ws = wb.active
        ws.title = 'Sheet1'
        ws.append(list(schema))
        for row in rows:
            ws.append([row.get(col, '') for col in schema])
        wb.save(dest)
        wb.close()

    def _write_groups(self, schema: Sequence[str], grouped: Dict[str, List[Dict[str, Any]]], base_dir: Path, stem: str) -> List[str]:
        exports: List[str] = []
        for key, rows in grouped.items():
            safe_key = key or '未分组'
            filename = f'{stem}_{safe_key}.xlsx'
            dest = base_dir / filename
            self._write_rows(schema, rows, dest)
            exports.append(str(dest))
        return exports

    def _write_chart_json(self, chart: Dict[str, Any], output_dir: Path, stem: str) -> str:
        json_path = output_dir / f'{stem}_chart.json'
        with json_path.open('w', encoding='utf-8') as fp:
            json.dump(chart, fp, ensure_ascii=False, indent=2)
        return str(json_path)

    def _build_chart(self, groups: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        labels: List[str] = []
        values: List[int] = []
        for key, rows in groups.items():
            labels.append(key or '未分组')
            values.append(len(rows))
        return {
            'labels': labels,
            'datasets': [
                {
                    'label': '分组数量',
                    'data': values
                }
            ],
            'generatedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    # -------- APIs --------

    def excel_preview(self, options: Dict = None):
        '''读取 Excel 表头与样例数据'''
        try:
            opts = self._validate_payload(options)
            file_path = opts.get('filePath', '')
            sheet_name = opts.get('sheetName')
            delimiter = opts.get('delimiter') or '|'

            source = self._ensure_excel_file(file_path)
            sheets = self._list_sheets(source)
            header, data_rows, active_sheet = self._load_sheet(source, sheet_name)
            schema = self._normalize_schema(opts.get('schemaText', ''), delimiter, header)
            rows = self._rows_to_dicts(schema, data_rows[:30], active_sheet)

            return {
                'code': 0,
                'msg': '解析完成',
                'schema': schema,
                'schemaText': delimiter.join(schema),
                'delimiter': delimiter,
                'rowCount': len(data_rows),
                'sheet': active_sheet,
                'sheets': sheets,
                'sample': rows
            }
        except Exception as exc:
            return {'code': -1, 'msg': f'解析失败：{exc}'}

    def excel_process(self, options: Dict = None):
        '''执行分组、排序与导出'''
        try:
            opts = self._validate_payload(options)
            source = self._ensure_excel_file(opts.get('filePath', ''))
            sheet_name = opts.get('sheetName')
            delimiter = opts.get('delimiter') or '|'
            schema_text = opts.get('schemaText', '')
            group_by = opts.get('groupBy') or ''
            sort_by = opts.get('sortBy') or ''
            sort_order = (opts.get('sortOrder') or 'asc').lower()
            export_groups = bool(opts.get('exportGroups', True))
            export_json = bool(opts.get('exportJson', True))
            export_combined = bool(opts.get('exportCombined', False))
            output_dir = self._ensure_output_dir(source, opts.get('outputDir', ''), 'excel')

            header, data_rows, active_sheet = self._load_sheet(source, sheet_name)
            schema = self._normalize_schema(schema_text, delimiter, header)
            records = self._rows_to_dicts(schema, data_rows, active_sheet)

            merge_files = opts.get('mergeFiles') or []
            if merge_files:
                merged = self._load_merge_tables(schema, merge_files)
                records.extend(merged)

            if sort_by and sort_by in schema:
                reverse = sort_order == 'desc'
                records.sort(key=lambda item: item.get(sort_by, ''), reverse=reverse)

            grouped = self._group_records(records, group_by)
            chart = self._build_chart(grouped) if group_by else {}
            group_files: List[str] = []
            if group_by and export_groups:
                group_dir = output_dir / 'groups'
                group_dir.mkdir(parents=True, exist_ok=True)
                group_files = self._write_groups(schema, grouped, group_dir, source.stem)

            json_path = ''
            if group_by and export_json and chart:
                json_path = self._write_chart_json(chart, output_dir, source.stem)

            combined_path = ''
            if export_combined:
                combined_path = str(output_dir / f'{source.stem}_combined.xlsx')
                self._write_rows(schema, records, Path(combined_path))

            summary = {
                'totalRows': len(records),
                'groupBy': group_by,
                'groupCount': len(grouped) if group_by else 0,
                'sortBy': sort_by,
                'sortOrder': sort_order
            }

            return {
                'code': 0,
                'msg': 'Excel 处理完成',
                'summary': summary,
                'schema': schema,
                'groups': [{'key': key, 'count': len(val)} for key, val in grouped.items()] if group_by else [],
                'groupFiles': group_files,
                'jsonPath': json_path,
                'chart': chart,
                'combinedPath': combined_path,
                'outputDir': str(output_dir)
            }
        except Exception as exc:
            return {'code': -1, 'msg': f'处理失败：{exc}'}

    def excel_merge_tables(self, options: Dict = None):
        '''将多个分表合并为主表'''
        try:
            opts = self._validate_payload(options)
            tables = opts.get('tables') or []
            if not tables:
                raise ValueError('请至少选择一个分表文件')
            first = tables[0]
            schema_text = opts.get('schemaText', '')
            delimiter = opts.get('delimiter') or '|'

            first_path = self._ensure_excel_file(first.get('path', ''))
            header, _, _ = self._load_sheet(first_path, first.get('sheet'))
            schema = self._normalize_schema(schema_text, delimiter, header)

            merged: List[Dict[str, Any]] = []
            for table in tables:
                table_path = self._ensure_excel_file(table.get('path', ''))
                sheet_name = table.get('sheet')
                _, rows, sheet = self._load_sheet(table_path, sheet_name)
                merged.extend(self._rows_to_dicts(schema, rows, sheet))

            output_dir = self._ensure_output_dir(first_path, opts.get('outputDir', ''), 'merged')
            filename = opts.get('outputName') or f'merged_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            dest = output_dir / (filename if filename.lower().endswith('.xlsx') else f'{filename}.xlsx')
            self._write_rows(schema, merged, dest)

            return {
                'code': 0,
                'msg': f'已合并 {len(tables)} 个分表',
                'output': str(dest),
                'rows': len(merged),
                'schema': schema
            }
        except Exception as exc:
            return {'code': -1, 'msg': f'合并失败：{exc}'}

    # -------- internal helpers --------

    def _list_sheets(self, file_path: Path) -> List[str]:
        wb = load_workbook(file_path, read_only=True)
        names = list(wb.sheetnames)
        wb.close()
        return names

    def _group_records(self, rows: List[Dict[str, Any]], group_by: str) -> Dict[str, List[Dict[str, Any]]]:
        if not group_by:
            return {}
        grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for row in rows:
            key = row.get(group_by) or ''
            grouped[key].append(row)
        return grouped

    def _load_merge_tables(self, schema: Sequence[str], tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        merged: List[Dict[str, Any]] = []
        for table in tables:
            table_path = self._ensure_excel_file(table.get('path', ''))
            sheet_name = table.get('sheet')
            _, rows, sheet = self._load_sheet(table_path, sheet_name)
            merged.extend(self._rows_to_dicts(schema, rows, sheet))
        return merged
