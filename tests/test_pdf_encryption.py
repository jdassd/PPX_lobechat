"""Real encrypted-PDF regressions for the PyPDF2-based page operations."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import fitz

from api.pdf import PDF


class PdfEncryptionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ppx-pdf-encryption-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def make_pdf(self, name, encryption, user_password="", owner_password="owner-secret"):
        path = self.root / name
        document = fitz.open()
        for text in ("encrypted-page-1", "encrypted-page-2", "encrypted-page-3"):
            page = document.new_page(width=240, height=180)
            page.insert_text((20, 40), text)
        document.save(
            path,
            encryption=encryption,
            owner_pw=owner_password,
            user_pw=user_password,
        )
        document.close()
        return path

    @staticmethod
    def page_texts(path):
        with fitz.open(path) as document:
            return [page.get_text().strip() for page in document]

    def test_owner_password_only_aes_128_and_256_work_in_all_page_operations(self):
        for encryption in (fitz.PDF_ENCRYPT_AES_128, fitz.PDF_ENCRYPT_AES_256):
            with self.subTest(encryption=encryption):
                source = self.make_pdf(f"owner-{encryption}.pdf", encryption)
                original_bytes = source.read_bytes()
                api = PDF()

                cut = api.pdf_cut({
                    "filePath": str(source), "mode": "custom", "pageSpec": "3,1",
                    "outputPath": str(self.root / f"cut-{encryption}.pdf"),
                })
                self.assertEqual(cut["code"], 0, cut)
                self.assertEqual(self.page_texts(cut["output"]), ["encrypted-page-3", "encrypted-page-1"])

                multi = api.pdf_multi_cut({
                    "filePath": str(source), "mode": "custom", "pageSpec": "3,1;2",
                    "outputDir": str(self.root / f"multi-{encryption}"),
                })
                self.assertEqual(multi["code"], 0, multi)
                self.assertEqual(
                    [self.page_texts(path) for path in multi["files"]],
                    [["encrypted-page-3", "encrypted-page-1"], ["encrypted-page-2"]],
                )

                split = api.pdf_split({
                    "filePath": str(source), "pagesPerFile": 2,
                    "outputDir": str(self.root / f"split-{encryption}"),
                })
                self.assertEqual(split["code"], 0, split)
                self.assertEqual(
                    [self.page_texts(path) for path in split["files"]],
                    [["encrypted-page-1", "encrypted-page-2"], ["encrypted-page-3"]],
                )

                merge_source = self.make_pdf(f"merge-{encryption}.pdf", encryption)
                merge_bytes = merge_source.read_bytes()
                merged = api.pdf_merge({
                    "files": [str(source), {"path": str(merge_source), "pageSpec": "2,1"}],
                    "outputPath": str(self.root / f"merge-result-{encryption}.pdf"),
                })
                self.assertEqual(merged["code"], 0, merged)
                self.assertEqual(
                    self.page_texts(merged["output"]),
                    ["encrypted-page-1", "encrypted-page-2", "encrypted-page-3", "encrypted-page-2", "encrypted-page-1"],
                )
                self.assertEqual(source.read_bytes(), original_bytes)
                self.assertEqual(merge_source.read_bytes(), merge_bytes)

    def test_password_argument_accepts_correct_password_and_reports_missing_or_wrong(self):
        source = self.make_pdf("user-password.pdf", fitz.PDF_ENCRYPT_AES_256, "open-secret")
        original_bytes = source.read_bytes()
        missing_output = self.root / "missing-password.pdf"
        missing = PDF().pdf_cut({
            "filePath": str(source), "pageSpec": "1", "mode": "custom",
            "outputPath": str(missing_output),
        })
        self.assertNotEqual(missing["code"], 0, missing)
        self.assertIn("请提供打开密码", missing["msg"])
        self.assertFalse(missing_output.exists())

        wrong_output = self.root / "wrong-password.pdf"
        wrong = PDF().pdf_cut({
            "filePath": str(source), "pageSpec": "1", "mode": "custom", "password": "wrong",
            "outputPath": str(wrong_output),
        })
        self.assertNotEqual(wrong["code"], 0, wrong)
        self.assertIn("密码错误", wrong["msg"])
        self.assertFalse(wrong_output.exists())

        correct = PDF().pdf_cut({
            "filePath": str(source), "pageSpec": "3,1", "mode": "custom", "password": "open-secret",
            "outputPath": str(self.root / "correct-password.pdf"),
        })
        self.assertEqual(correct["code"], 0, correct)
        self.assertEqual(self.page_texts(correct["output"]), ["encrypted-page-3", "encrypted-page-1"])

        multi = PDF().pdf_multi_cut({
            "filePath": str(source), "mode": "custom", "pageSpec": "3,1;2",
            "password": "open-secret", "outputDir": str(self.root / "password-multi"),
        })
        self.assertEqual(multi["code"], 0, multi)
        self.assertEqual(
            [self.page_texts(path) for path in multi["files"]],
            [["encrypted-page-3", "encrypted-page-1"], ["encrypted-page-2"]],
        )

        split = PDF().pdf_split({
            "filePath": str(source), "pagesPerFile": 2, "password": "open-secret",
            "outputDir": str(self.root / "password-split"),
        })
        self.assertEqual(split["code"], 0, split)
        self.assertEqual(
            [self.page_texts(path) for path in split["files"]],
            [["encrypted-page-1", "encrypted-page-2"], ["encrypted-page-3"]],
        )

        second_source = self.make_pdf(
            "second-user-password.pdf", fitz.PDF_ENCRYPT_AES_128, "second-secret"
        )
        second_bytes = second_source.read_bytes()
        merged = PDF().pdf_merge({
            "files": [
                {"path": str(source), "password": "open-secret", "pageSpec": "2,1"},
                {"path": str(second_source), "sourcePassword": "second-secret", "pageSpec": "3"},
            ],
            "outputPath": str(self.root / "password-merge.pdf"),
        })
        self.assertEqual(merged["code"], 0, merged)
        self.assertEqual(
            self.page_texts(merged["output"]),
            ["encrypted-page-2", "encrypted-page-1", "encrypted-page-3"],
        )
        self.assertEqual(source.read_bytes(), original_bytes)
        self.assertEqual(second_source.read_bytes(), second_bytes)

    def test_plain_pdf_ignores_password_argument_and_preserves_existing_output(self):
        source = self.make_pdf("plain.pdf", fitz.PDF_ENCRYPT_NONE)
        output = self.root / "existing-output.pdf"
        output.write_bytes(b"keep this existing output")

        result = PDF().pdf_cut({
            "filePath": str(source), "mode": "custom", "pageSpec": "2,1",
            "password": "irrelevant", "outputPath": str(output),
        })

        self.assertEqual(result["code"], 0, result)
        self.assertEqual(output.read_bytes(), b"keep this existing output")
        self.assertEqual(self.page_texts(result["output"]), ["encrypted-page-2", "encrypted-page-1"])
        self.assertNotEqual(result["output"], str(output))

        original_source = source.read_bytes()
        same_path = PDF().pdf_cut({
            "filePath": str(source), "mode": "custom", "pageSpec": "2,1",
            "password": "irrelevant", "outputPath": str(source),
        })
        self.assertEqual(same_path["code"], 0, same_path)
        self.assertNotEqual(same_path["output"], str(source))
        self.assertEqual(source.read_bytes(), original_source)
        self.assertEqual(self.page_texts(source), ["encrypted-page-1", "encrypted-page-2", "encrypted-page-3"])

    def test_unicode_pdf_password_is_accepted(self):
        password = "中文😀密碼"
        source = self.make_pdf("unicode-password.pdf", fitz.PDF_ENCRYPT_AES_256, password)

        result = PDF().pdf_cut({
            "filePath": str(source), "mode": "custom", "pageSpec": "3,1",
            "password": password, "outputPath": str(self.root / "unicode-cut.pdf"),
        })

        self.assertEqual(result["code"], 0, result)
        self.assertEqual(self.page_texts(result["output"]), ["encrypted-page-3", "encrypted-page-1"])

    def test_missing_crypto_provider_returns_chinese_dependency_error(self):
        source = self.make_pdf("blocked-provider.pdf", fitz.PDF_ENCRYPT_AES_256)
        script = r'''
import builtins
real_import = builtins.__import__
def blocked_import(name, *args, **kwargs):
    if name == "Crypto" or name.startswith("Crypto.") or name == "Cryptodome" or name.startswith("Cryptodome."):
        raise ModuleNotFoundError("blocked crypto provider for regression")
    return real_import(name, *args, **kwargs)
builtins.__import__ = blocked_import
from api.pdf import PDF
import sys
result = PDF().pdf_cut({"filePath": sys.argv[1], "mode": "custom", "pageSpec": "1"})
print(result["code"])
print(result["msg"])
'''
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, "-c", script, str(source)],
            cwd=Path(__file__).resolve().parents[1],
            env=environment,
            capture_output=True,
            encoding="utf-8",
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("-1", result.stdout)
        self.assertIn("缺少 PyCryptodome", result.stdout)
        self.assertNotIn("PyCryptodome is required for AES algorithm", result.stdout)


if __name__ == "__main__":
    unittest.main()
