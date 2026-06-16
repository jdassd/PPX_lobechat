#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Codex
Date: 2025-11-11
Description: Excel 工具相关 API
'''

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from openpyxl import Workbook, load_workbook

from api.utils.validators import ensure_output_directory


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
        # 复用通用输出目录创建逻辑，保持与其它模块一致
        return ensure_output_directory(source, preferred, suffix)

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

    def _coerce_number(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(str(value).replace(',', '').strip())
        except Exception:
            return None

    def _build_echarts_option(
        self,
        chart_type: str,
        labels: List[str],
        values: List[float],
        rows: List[Dict[str, Any]],
        series_label: str
    ) -> Dict[str, Any]:
        if chart_type == 'pie':
            return {
                'tooltip': {'trigger': 'item'},
                'legend': {'top': 'bottom'},
                'series': [
                    {
                        'name': series_label,
                        'type': 'pie',
                        'radius': ['35%', '70%'],
                        'data': rows,
                        'label': {'formatter': '{b}: {c}'}
                    }
                ]
            }
        return {
            'tooltip': {'trigger': 'axis'},
            'grid': {'left': '3%', 'right': '4%', 'bottom': '3%', 'containLabel': True},
            'xAxis': {'type': 'category', 'data': labels},
            'yAxis': {'type': 'value'},
            'series': [
                {
                    'name': series_label,
                    'type': chart_type,
                    'data': values,
                    'smooth': chart_type == 'line'
                }
            ]
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

    def excel_chart_build(self, options: Dict = None):
        '''构建 ECharts 图表数据'''
        try:
            opts = self._validate_payload(options)
            source = self._ensure_excel_file(opts.get('filePath', ''))
            sheet_name = opts.get('sheetName')
            delimiter = opts.get('delimiter') or '|'
            schema_text = opts.get('schemaText', '')
            chart_type = (opts.get('chartType') or 'bar').lower()
            dimension = opts.get('dimension') or ''
            metric = opts.get('metric') or ''
            aggregate = (opts.get('aggregate') or 'sum').lower()

            if chart_type not in ('bar', 'line', 'pie'):
                raise ValueError('仅支持 bar / line / pie 图表')
            if not dimension:
                raise ValueError('请选择维度列')

            header, data_rows, active_sheet = self._load_sheet(source, sheet_name)
            schema = self._normalize_schema(schema_text, delimiter, header)

            if dimension not in schema:
                raise ValueError(f'维度列不存在：{dimension}')
            if aggregate in ('sum', 'avg'):
                if not metric:
                    raise ValueError('请选择数值列')
                if metric not in schema:
                    raise ValueError(f'数值列不存在：{metric}')

            records = self._rows_to_dicts(schema, data_rows, active_sheet)
            order: List[str] = []
            counts: Dict[str, int] = {}
            sums: Dict[str, float] = {}
            for row in records:
                key = str(row.get(dimension) or '').strip() or '未分类'
                if key not in counts:
                    order.append(key)
                    counts[key] = 0
                    sums[key] = 0.0
                counts[key] += 1
                if aggregate in ('sum', 'avg'):
                    value = self._coerce_number(row.get(metric))
                    if value is not None:
                        sums[key] += value

            rows: List[Dict[str, Any]] = []
            for key in order:
                if aggregate == 'count':
                    value = counts.get(key, 0)
                elif aggregate == 'avg':
                    total = sums.get(key, 0.0)
                    value = round(total / counts.get(key, 1), 4) if counts.get(key, 0) else 0
                else:
                    value = round(sums.get(key, 0.0), 4)
                rows.append({'name': key, 'value': value})

            labels = [item['name'] for item in rows]
            values = [item['value'] for item in rows]

            aggregate_label = {'sum': '求和', 'avg': '均值', 'count': '计数'}.get(aggregate, '求和')
            metric_label = metric or '记录'
            series_label = f'{metric_label} · {aggregate_label}'
            option = self._build_echarts_option(chart_type, labels, values, rows, series_label)

            return {
                'code': 0,
                'msg': '图表数据生成完成',
                'schema': schema,
                'sheet': active_sheet,
                'data': {
                    'dimension': dimension,
                    'metric': metric,
                    'aggregate': aggregate,
                    'rows': rows,
                    'generatedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                },
                'option': option
            }
        except Exception as exc:
            return {'code': -1, 'msg': f'生成失败：{exc}'}

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

    def excel_column_profile(self, options: Dict = None):
        '''列统计分析'''
        try:
            opts = self._validate_payload(options)
            source = self._ensure_excel_file(opts.get('filePath', ''))
            sheet_name = opts.get('sheetName')
            delimiter = opts.get('delimiter') or '|'
            schema_text = opts.get('schemaText', '')
            header, data_rows, active_sheet = self._load_sheet(source, sheet_name)
            schema = self._normalize_schema(schema_text, delimiter, header)
            target_columns = opts.get('columns') or schema
            columns = [col for col in target_columns if col in schema]
            if not columns:
                columns = schema
            records = self._rows_to_dicts(schema, data_rows, active_sheet)
            total_rows = len(records)
            profiles = []
            for column in columns:
                values = [str(row.get(column, '') or '').strip() for row in records]
                blanks = sum(1 for value in values if not value)
                non_blank = [value for value in values if value]
                unique_count = len(set(non_blank))
                numeric_values = []
                for value in non_blank:
                    try:
                        numeric_values.append(float(value.replace(',', '')))
                    except Exception:
                        continue
                is_numeric = len(numeric_values) >= max(1, int(0.6 * len(non_blank))) if non_blank else False
                counter = Counter(non_blank)
                top_values = [
                    {'value': key, 'count': count, 'ratio': round(count / total_rows, 4)}
                    for key, count in counter.most_common(5)
                ]
                numeric_summary = {}
                if numeric_values:
                    numeric_summary = {
                        'min': min(numeric_values),
                        'max': max(numeric_values),
                        'avg': round(sum(numeric_values) / len(numeric_values), 4)
                    }
                profiles.append({
                    'field': column,
                    'type': 'number' if is_numeric else 'text',
                    'unique': unique_count,
                    'blanks': blanks,
                    'blankRatio': round(blanks / total_rows, 4) if total_rows else 0,
                    'topValues': top_values,
                    'numeric': numeric_summary,
                    'samples': non_blank[:5]
                })
            return {
                'code': 0,
                'msg': '列分析完成',
                'summary': {
                    'sheet': active_sheet,
                    'totalRows': total_rows,
                    'columns': len(columns)
                },
                'profiles': profiles
            }
        except Exception as exc:
            return {'code': -1, 'msg': f'分析失败：{exc}'}

    def excel_split_by_column(self, options: Dict = None):
        '''按列拆分为多个工作簿'''
        try:
            opts = self._validate_payload(options)
            source = self._ensure_excel_file(opts.get('filePath', ''))
            column = opts.get('column') or opts.get('groupBy')
            if not column:
                raise ValueError('请选择需要拆分的列')
            sheet_name = opts.get('sheetName')
            delimiter = opts.get('delimiter') or '|'
            schema_text = opts.get('schemaText', '')
            header, data_rows, active_sheet = self._load_sheet(source, sheet_name)
            schema = self._normalize_schema(schema_text, delimiter, header)
            if column not in schema:
                raise ValueError(f'列不存在：{column}')
            records = self._rows_to_dicts(schema, data_rows, active_sheet)
            limit = int(opts.get('limit') or 0)
            min_rows = int(opts.get('minRows') or 1)
            empty_label = opts.get('emptyLabel') or '未分类'
            output_dir = self._ensure_output_dir(source, opts.get('outputDir', ''), 'split')
            groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            for row in records:
                key = str(row.get(column) or '').strip() or empty_label
                groups[key].append(row)
            sorted_groups = sorted(groups.items(), key=lambda item: len(item[1]), reverse=True)
            if limit > 0:
                sorted_groups = sorted_groups[:limit]
            exports = []
            for label, rows in sorted_groups:
                if len(rows) < min_rows:
                    continue
                safe_label = ''.join(ch if ch.isalnum() else '_' for ch in label) or 'group'
                dest = output_dir / f'{column}_{safe_label}.xlsx'
                self._write_rows(schema, rows, dest)
                exports.append({'label': label, 'rows': len(rows), 'file': str(dest)})
            if not exports:
                raise ValueError('没有满足条件的分组可导出')
            return {
                'code': 0,
                'msg': f'已导出 {len(exports)} 个分组',
                'groups': [{'label': item['label'], 'rows': item['rows']} for item in exports],
                'files': [item['file'] for item in exports],
                'outputDir': str(output_dir)
            }
        except Exception as exc:
            return {'code': -1, 'msg': f'拆分失败：{exc}'}

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
