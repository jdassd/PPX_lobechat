"""Repair the embedded PDF payload used by CNKI CAJ containers.

The container offsets and missing-page-tree behavior follow the CAJ layout
documented by caj2pdf/caj2pdf at revision
6c4bc32b15ce748d211f45d536f5d5511ef9f368. This implementation uses PyMuPDF
for xref recovery and does not include the upstream Qt GUI or native decoders.
"""
from __future__ import annotations

import re
import struct

import fitz

_OBJECT_RE = re.compile(rb"(?:\A|[\r\n])(\d+)\s+0\s+obj\b(.*?)endobj", re.S)
_PARENT_RE = re.compile(rb"/Parent\s+(\d+)\s+\d+\s+R\b")
_TYPE_RE = re.compile(rb"/Type\s*/(Page|Pages)\b")


def _read_i32(data: bytes, offset: int, label: str) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError(f'CAJ 文件结构损坏：{label}偏移越界')
    return struct.unpack_from('<i', data, offset)[0]


def _extract_embedded_pdf(data: bytes) -> tuple[bytes, int]:
    """Extract CAJ's object stream and synthesize the missing page tree."""
    if len(data) < 4:
        raise ValueError('CAJ 文件结构损坏：文件头不完整')
    magic = data[:4]
    if magic.startswith(b'HN') or magic.startswith(b'\xc8'):
        raise ValueError('暂不支持 HN/C8 格式 CAJ；当前版本支持内嵌 PDF 的 CAJ 文件')
    if magic != b'CAJ\x00' and not magic.startswith(b'CAJ'):
        raise ValueError('不支持的 CAJ 文件格式')

    page_count = _read_i32(data, 0x10, '页数')
    pointer_offset = _read_i32(data, 0x14, 'PDF 起始指针')
    if page_count <= 0 or page_count > 1_000_000:
        raise ValueError('CAJ 文件结构损坏：页数无效')
    embedded_offset = _read_i32(data, pointer_offset, 'PDF 数据偏移')
    if embedded_offset < 0x18 or embedded_offset >= len(data):
        raise ValueError('CAJ 文件结构损坏：PDF 数据偏移越界')

    end_marker = data.rfind(b'endobj', embedded_offset)
    if end_marker < embedded_offset:
        raise ValueError('CAJ 文件结构损坏：找不到内嵌 PDF 对象')
    object_bytes = data[embedded_offset:end_marker + len(b'endobj')]
    matches = list(_OBJECT_RE.finditer(object_bytes))
    if not matches:
        raise ValueError('CAJ 文件结构损坏：内嵌 PDF 对象无法解析')

    objects: dict[int, tuple[bytes, bytes]] = {}
    for match in matches:
        number = int(match.group(1))
        body = match.group(2)
        objects[number] = (match.group(0), body)

    node_types = {number: match.group(1) for number, (_, body) in objects.items()
                  if (match := _TYPE_RE.search(body.split(b'stream', 1)[0]))}
    # Object IDs need not follow reading order. Preserve their order in the
    # payload when recovering missing /Kids arrays, as the upstream reader does.
    page_objects = [number for number, kind in node_types.items() if kind == b'Page']
    if not page_objects:
        raise ValueError('CAJ 文件结构损坏：内嵌 PDF 中没有页面对象')

    # Upstream CAJ files commonly omit the Catalog and the top /Pages object.
    # Recover the parent references from page objects and build the missing
    # /Pages dictionaries around the original page objects, preserving content.
    parent_refs: dict[int, list[int]] = {}
    for number in node_types:
        body = objects[number][1]
        match = _PARENT_RE.search(body)
        if match:
            parent_refs.setdefault(int(match.group(1)), []).append(number)
    if not parent_refs:
        raise ValueError('CAJ 文件结构损坏：页面对象缺少 /Parent 引用')

    missing_parents = [parent for parent in parent_refs if parent not in objects]
    pages_nodes = [number for number, kind in node_types.items() if kind == b'Pages']
    root_pages = [number for number in pages_nodes if not _PARENT_RE.search(objects[number][1])]
    additions: list[bytes] = []
    next_number = max([*objects, *parent_refs]) + 1

    def count_pages(number, visiting=None):
        if node_types.get(number) == b'Page':
            return 1
        visiting = set() if visiting is None else visiting
        if number in visiting:
            raise ValueError('CAJ 文件结构损坏：页面树存在循环引用')
        return sum(count_pages(child, visiting | {number}) for child in parent_refs.get(number, []))

    roots = root_pages + missing_parents
    if not roots:
        raise ValueError('CAJ 文件结构损坏：找不到页面树根节点')
    root_number = roots[0] if len(roots) == 1 else next_number
    for parent in missing_parents:
        kids = parent_refs[parent]
        parent_link = f'/Parent {root_number} 0 R ' if parent != root_number else ''
        additions.append(
            f'{parent} 0 obj\r<< /Type /Pages {parent_link}/Kids [{" ".join(f"{kid} 0 R" for kid in kids)}] '
            f'/Count {count_pages(parent)} >>\rendobj\r'.encode('ascii')
        )
    if len(roots) > 1:
        for number in root_pages:
            body = objects[number][1].replace(b'<<', f'<< /Parent {root_number} 0 R '.encode(), 1)
            additions.append(f'{number} 0 obj\r'.encode() + body + b'\rendobj\r')
        additions.append(
            f'{root_number} 0 obj\r<< /Type /Pages /Kids [{" ".join(f"{kid} 0 R" for kid in roots)}] '
            f'/Count {page_count} >>\rendobj\r'.encode('ascii')
        )

    has_catalog = any(re.search(rb'/Type\s*/Catalog\b', body) for _, body in objects.values())
    if not has_catalog:
        catalog_number = max([*objects, root_number, *missing_parents], default=0) + 1
        additions.append(
            f'{catalog_number} 0 obj\r<< /Type /Catalog /Pages {root_number} 0 R >>\rendobj\r'.encode('ascii')
        )

    return b'%PDF-1.3\r\n' + object_bytes + b'\r\n' + b''.join(additions) + b'\n%%EOF\r\n', page_count


def caj_to_pdf_bytes(data: bytes) -> bytes:
    """Convert a CAJ payload containing PDF objects into a repaired PDF."""
    if data.startswith(b'%PDF-'):
        pdf_data = data
        expected_pages = None
    else:
        pdf_data, expected_pages = _extract_embedded_pdf(data)
    try:
        with fitz.open(stream=pdf_data, filetype='pdf') as document:
            if document.is_encrypted:
                raise ValueError('加密的 PDF 内容无法从 CAJ 中转换')
            actual_pages = document.page_count
            if not actual_pages or (expected_pages is not None and actual_pages != expected_pages):
                raise ValueError(f'PDF 页面树修复失败（CAJ 记录 {expected_pages} 页，实际读取 {actual_pages} 页）')
            output = document.tobytes(garbage=4, deflate=True)
        # Reopen the result before publishing so malformed output never escapes.
        with fitz.open(stream=output, filetype='pdf') as verified:
            if verified.page_count != actual_pages:
                raise ValueError('PDF 输出校验失败：页面数量不一致')
        return output
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f'无法解析 CAJ 内嵌 PDF：{exc}') from exc
