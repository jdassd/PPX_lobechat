"""PDF workflow definitions must not persist open passwords."""

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from api.workflow import WorkflowMixin
from pyapp.config.config import Config


class WorkflowApi(WorkflowMixin):
    pass


class PdfWorkflowSecretTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ppx-pdf-workflow-secrets-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.config_patch = mock.patch.object(Config, "appDataDir", str(self.root / "state"))
        self.config_patch.start()
        self.addCleanup(self.config_patch.stop)
        self.api = WorkflowApi()
        self.addCleanup(self.api.workflow_stop)

    def assert_password_absent_from_state_database(self, password):
        database = self.root / "state" / "workbench.sqlite3"
        with sqlite3.connect(database) as connection:
            values = []
            for table in ("state_meta", "state_records"):
                values.extend(row[0] for row in connection.execute(f"SELECT payload FROM {table}"))
        self.assertNotIn(password, "\n".join(values))

    def test_save_rejects_pdf_passwords_without_persisting_them(self):
        password = "workflow-test-password-秘密"
        cases = (
            ("pdf_cut", {"password": password}),
            ("pdf_split", {"sourcePassword": password}),
            ("pdf_multi_cut", {"password": "", "nested": [{"sourcePassword": password}]}),
            ("pdf_merge", {"files": [{"path": "secret.pdf", "password": password}]}),
            ("pdf_merge", {"files": [{"path": "secret.pdf", "sourcePassword": password}]}),
        )

        for method, args in cases:
            with self.subTest(method=method, args=args):
                result = self.api.workflow_save({
                    "name": "secret workflow",
                    "steps": [{"id": "step", "method": method, "args": args}],
                })
                self.assertNotEqual(result["code"], 0, result)
                self.assertIn("工作流不会保存密码", result["msg"])
                self.assert_password_absent_from_state_database(password)

    def test_empty_pdf_passwords_remain_saveable(self):
        result = self.api.workflow_save({"name": "empty password", "steps": [
            {"id": "cut", "method": "pdf_cut", "args": {"password": ""}},
            {"id": "merge", "method": "pdf_merge", "args": {"files": [
                {"path": "a.pdf", "password": None}, {"path": "b.pdf", "sourcePassword": ""},
            ]}},
        ]})
        self.assertEqual(result["code"], 0, result)

    def test_import_rejects_passwords_before_database_persistence(self):
        password = "bundle-secret-秘密"
        bundle = self.root / "input.json"
        bundle.write_text(json.dumps({
            "type": "ppx-workflow-bundle",
            "schemaVersion": 1,
            "workflows": [{
                "id": "imported",
                "name": "secret import",
                "steps": [{"id": "merge", "method": "pdf_merge", "args": {
                    "files": [{"path": "a.pdf"}, {"path": "b.pdf", "sourcePassword": password}],
                }}],
            }],
        }, ensure_ascii=False), encoding="utf-8")

        result = self.api.workflow_bundle_import({"filePath": str(bundle)})

        self.assertNotEqual(result["code"], 0, result)
        self.assertIn("工作流不会保存密码", result["msg"])
        self.assert_password_absent_from_state_database(password)
        self.assertEqual(self.api.workflow_list()["workflows"], [])


if __name__ == "__main__":
    unittest.main()
