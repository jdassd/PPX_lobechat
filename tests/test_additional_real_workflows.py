"""Additional filesystem workflows exercised against real temporary files."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from api.document_index import DocumentIndexMixin
from api.file import FileTool
from pyapp.config.config import Config


class AdditionalRealWorkflowTests(unittest.TestCase):
    def test_delete_preview_recycle_and_conflict_safe_restore(self):
        with tempfile.TemporaryDirectory(prefix="ppx 文件恢复 ") as directory:
            root = Path(directory).resolve()
            source = root / "待恢复 文件.txt"
            source.write_text("原始内容", encoding="utf-8")
            tool = FileTool()
            options = {"directory": str(root), "extensions": ["txt"], "dryRun": True}

            preview = tool.file_batch_delete(options)
            self.assertEqual(preview["code"], 0, preview)
            self.assertEqual(preview["count"], 1)
            self.assertEqual(preview["preview"], [str(source)])
            self.assertEqual(source.read_text(encoding="utf-8"), "原始内容")
            self.assertFalse((root / ".ppx_recycle").exists())

            deleted = tool.file_batch_delete({**options, "dryRun": False})
            self.assertEqual(deleted["code"], 0, deleted)
            self.assertFalse(source.exists())
            batch = tool.file_recycle_list({"directory": str(root)})["batches"][0]
            self.assertEqual(batch["id"], deleted["id"])
            self.assertEqual(batch["count"], 1)

            source.write_text("新文件内容", encoding="utf-8")
            restored = tool.file_recycle_restore(
                {"directory": str(root), "id": deleted["id"], "conflictPolicy": "rename"}
            )
            restored_path = root / "待恢复 文件_restored_1.txt"
            self.assertEqual(restored["code"], 0, restored)
            self.assertEqual(restored["restoredCount"], 1)
            self.assertEqual(source.read_text(encoding="utf-8"), "新文件内容")
            self.assertEqual(restored_path.read_text(encoding="utf-8"), "原始内容")
            self.assertEqual(tool.file_recycle_list({"directory": str(root)})["batches"], [])

    def test_classify_copy_collision_and_undo_preserve_source_bytes(self):
        with tempfile.TemporaryDirectory(prefix="ppx 分类流程 ") as directory:
            root = Path(directory).resolve()
            source = root / "输入目录"
            (source / "甲").mkdir(parents=True)
            (source / "乙").mkdir()
            first = source / "甲" / "报告.txt"
            second = source / "乙" / "报告.txt"
            first.write_bytes("第一份\n".encode())
            second.write_bytes("第二份\n".encode())
            first_before, second_before = first.read_bytes(), second.read_bytes()
            target = root / "分类结果"
            tool = FileTool()
            options = {
                "directory": str(source),
                "targetDir": str(target),
                "typeMap": [{"label": "文档", "extensions": ["txt"]}],
                "operation": "copy",
            }

            preview = tool.file_auto_classify({**options, "dryRun": True})
            self.assertEqual(preview["code"], 0, preview)
            self.assertEqual(len(preview["operations"]), 2)
            self.assertTrue(first.is_file() and second.is_file())
            self.assertFalse(target.exists())

            existing_target = target / "文档" / "报告.txt"
            existing_target.parent.mkdir(parents=True)
            existing_target.write_bytes("预先存在的目标".encode())
            classified = tool.file_auto_classify(options)
            self.assertEqual(classified["code"], 0, classified)
            destinations = [Path(item["to"]) for item in classified["operations"]]
            self.assertEqual({path.name for path in destinations}, {"报告_2.txt", "报告_3.txt"})
            self.assertEqual({path.read_bytes() for path in destinations}, {first_before, second_before})
            self.assertEqual(existing_target.read_bytes(), "预先存在的目标".encode())
            self.assertEqual(first.read_bytes(), first_before)
            self.assertEqual(second.read_bytes(), second_before)

            undone = tool.file_classify_undo(
                {"directory": str(source), "transactionId": classified["transactionId"]}
            )
            self.assertEqual(undone["code"], 0, undone)
            self.assertEqual(undone["restoredCount"], 2)
            self.assertEqual(undone["undoneCount"], 2)
            self.assertEqual(undone["removedCount"], 2)
            self.assertIn("成功撤销 2 项", undone["msg"])
            self.assertTrue(first.is_file() and second.is_file())
            self.assertEqual(first.read_bytes(), first_before)
            self.assertEqual(second.read_bytes(), second_before)
            self.assertEqual(existing_target.read_bytes(), "预先存在的目标".encode())
            self.assertFalse(any(path.exists() for path in destinations))

    def test_classify_preview_does_not_create_default_target_and_rejects_file_target(self):
        with tempfile.TemporaryDirectory(prefix="ppx 分类预览 ") as directory:
            root = Path(directory).resolve()
            source = root / "输入"
            source.mkdir()
            file = source / "说明.txt"
            file.write_text("保留内容", encoding="utf-8")
            tool = FileTool()

            preview = tool.file_auto_classify({"directory": str(source), "dryRun": True})
            self.assertEqual(preview["code"], 0, preview)
            self.assertFalse((source / "_classified").exists())

            invalid_target = root / "不是目录"
            invalid_target.write_bytes(b"keep")
            rejected = tool.file_auto_classify({
                "directory": str(source), "targetDir": str(invalid_target), "dryRun": True,
            })
            self.assertNotEqual(rejected["code"], 0, rejected)
            self.assertEqual(invalid_target.read_bytes(), b"keep")

    def test_document_index_prune_removes_only_missing_sources_in_requested_root(self):
        with tempfile.TemporaryDirectory(prefix="ppx 索引维护 ") as directory:
            root = Path(directory).resolve()
            app_data = root / "应用数据"
            first_root = root / "文档甲"
            second_root = root / "文档乙"
            app_data.mkdir()
            first_root.mkdir()
            second_root.mkdir()
            first = first_root / "说明 文件.txt"
            second = second_root / "说明 文件.txt"
            first.write_text("第一目录中的独有词", encoding="utf-8")
            second.write_text("第二目录中的独有词", encoding="utf-8")

            with mock.patch.object(Config, "appDataDir", str(app_data)):
                index = DocumentIndexMixin()
                built = index.document_index_build({"directories": [str(first_root), str(second_root)]})
                self.assertEqual(built["code"], 0, built)
                first.unlink()
                pruned = index.document_index_build({"directories": [str(first_root)], "prune": True})
                status = index.document_index_status()
                first_hits = index.document_index_search({"query": "第一目录中的独有词"})
                second_hits = index.document_index_search({"query": "第二目录中的独有词"})

            self.assertEqual(pruned["code"], 0, pruned)
            self.assertEqual(status["documents"], 1)
            self.assertEqual(status["missingDocuments"], 0)
            self.assertEqual(first_hits["results"], [])
            self.assertEqual([item["path"] for item in second_hits["results"]], [str(second.resolve())])
            self.assertEqual(second.read_text(encoding="utf-8"), "第二目录中的独有词")


if __name__ == "__main__":
    unittest.main()
