"""Build and run a tiny frozen PyPDF2 AES probe with the product's Crypto collection."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import fitz

PRODUCT_CRYPTO_HIDDEN_IMPORTS = [
    'Crypto.Cipher.AES',
    'Crypto.Cipher.ARC4',
    'Crypto.Util.Padding',
]

PROBE_SOURCE = '''\
from pathlib import Path
import sys
from PyPDF2 import PdfReader

password = "ppx-aes-freeze-probe"
fixtures = Path(sys._MEIPASS) / "fixtures"
for name in ("aes128.pdf", "aes256.pdf"):
    reader = PdfReader(str(fixtures / name))
    if not reader.is_encrypted or not reader.decrypt(password):
        raise RuntimeError(f"{name} did not decrypt")
    if len(reader.pages) != 1 or "Frozen AES PDF content" not in reader.pages[0].extract_text():
        raise RuntimeError(f"{name} page content could not be read")
    print(f"{name}: encrypted page text read successfully")
'''


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    report_dir = root / 'build' / 'verification'
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / 'pdf-aes-freeze.json'
    build_log_path = report_dir / 'pdf-aes-freeze-build.log'
    run_log_path = report_dir / 'pdf-aes-freeze-run.log'
    report = {
        'passed': False,
        'platform': sys.platform,
        'python': sys.version.split()[0],
        'startedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'fixtureAlgorithms': ['AES-128', 'AES-256'],
        'buildLog': str(build_log_path.relative_to(root)).replace('\\', '/'),
        'runLog': str(run_log_path.relative_to(root)).replace('\\', '/'),
    }
    try:
        with tempfile.TemporaryDirectory(prefix='ppx-pdf-aes-freeze-') as temporary:
            work = Path(temporary)
            source = work / 'pdf_aes_probe.py'
            source.write_text(PROBE_SOURCE, encoding='utf-8')
            fixtures = work / 'fixtures'
            fixtures.mkdir()
            for filename, encryption in (
                ('aes128.pdf', fitz.PDF_ENCRYPT_AES_128),
                ('aes256.pdf', fitz.PDF_ENCRYPT_AES_256),
            ):
                document = fitz.open()
                document.new_page().insert_text((72, 72), 'Frozen AES PDF content')
                document.save(
                    str(fixtures / filename),
                    encryption=encryption,
                    user_pw='ppx-aes-freeze-probe',
                    owner_pw='ppx-aes-freeze-owner',
                )
                document.close()
            dist = work / 'dist'
            build = work / 'build'
            spec = work / 'spec'
            command = [
                sys.executable,
                '-m',
                'PyInstaller',
                '--clean',
                '--noconfirm',
                '--onefile',
                '--name',
                'pdf_aes_probe',
                '--distpath',
                str(dist),
                '--workpath',
                str(build),
                '--specpath',
                str(spec),
                '--add-data',
                f'{fixtures / "aes128.pdf"}{os.pathsep}fixtures',
                '--add-data',
                f'{fixtures / "aes256.pdf"}{os.pathsep}fixtures',
            ]
            for module in PRODUCT_CRYPTO_HIDDEN_IMPORTS:
                command.extend(['--hidden-import', module])
            command.append(str(source))
            report['buildCommand'] = [Path(sys.executable).name, '-m', 'PyInstaller', '--onefile',
                                     '--hidden-import', 'Crypto.Cipher.AES',
                                     '--hidden-import', 'Crypto.Cipher.ARC4',
                                     '--hidden-import', 'Crypto.Util.Padding']
            with build_log_path.open('w', encoding='utf-8') as build_log:
                subprocess.run(command, cwd=root, stdout=build_log, stderr=subprocess.STDOUT,
                               text=True, check=True)

            executable = dist / ('pdf_aes_probe.exe' if os.name == 'nt' else 'pdf_aes_probe')
            with run_log_path.open('w', encoding='utf-8') as run_log:
                subprocess.run([str(executable)], cwd=work, stdout=run_log,
                               stderr=subprocess.STDOUT, text=True, check=True)
            output = run_log_path.read_text(encoding='utf-8')
            for filename in ('aes128.pdf', 'aes256.pdf'):
                if f'{filename}: encrypted page text read successfully' not in output:
                    raise RuntimeError(f'Frozen probe did not report successful content read: {filename}')
            report.update(passed=True, completedChecks=['AES-128 decrypt and page text',
                                                        'AES-256 decrypt and page text'])
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        report['buildLogTail'] = _tail(build_log_path)
        report['runLogTail'] = _tail(run_log_path)
        _write_report(report_path, report)
        raise
    report['finishedAt'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    _write_report(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def _tail(path: Path, limit: int = 30) -> list[str]:
    if not path.is_file():
        return []
    return path.read_text(encoding='utf-8', errors='replace').splitlines()[-limit:]


def _write_report(path: Path, report: dict) -> None:
    report['finishedAt'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
