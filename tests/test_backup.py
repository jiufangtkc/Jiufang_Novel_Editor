import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.models import JneProject, ProjectInfo, ChapterNode
from services.database import DatabaseService
from services.backup_service import BackupService


class TestBackupService(unittest.TestCase):
    def _create_sample_project(self):
        project = JneProject(
            project_info=ProjectInfo(
                title="備份測試專案",
                logline="這是一部備份測試作品"
            ),
            current_theme="forest"
        )
        ch = ChapterNode(name="第一章", node_type="file", content="這是一段備份測試內容。")
        project.tree.append(ch)
        return project

    def test_create_and_inspect_backup(self):
        sample_project = self._create_sample_project()
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "my_novel.db")
            DatabaseService.save_project(sample_project, db_path)

            zip_path = os.path.join(tmpdir, "my_novel_backup.zip")
            out_path = BackupService.create_backup(
                project_db_path=db_path,
                backup_zip_path=zip_path,
                project_title="備份測試專案"
            )
            self.assertTrue(os.path.isfile(out_path))
            self.assertEqual(out_path, zip_path)

            # 檢查 Manifest
            manifest = BackupService.inspect_backup(zip_path)
            self.assertEqual(manifest["project_title"], "備份測試專案")
            self.assertEqual(manifest["original_db_filename"], "my_novel.db")
            self.assertEqual(len(manifest["db_entries"]), 1)

    def test_restore_backup_and_load(self):
        sample_project = self._create_sample_project()
        with tempfile.TemporaryDirectory() as tmpdir:
            src_db_path = os.path.join(tmpdir, "src_novel.db")
            DatabaseService.save_project(sample_project, src_db_path)

            zip_path = os.path.join(tmpdir, "backup.zip")
            BackupService.create_backup(src_db_path, zip_path, project_title="備份測試專案")

            restore_target_dir = os.path.join(tmpdir, "restored_dir")
            restored_db_path = BackupService.restore_backup(
                backup_zip_path=zip_path,
                target_dir=restore_target_dir,
                custom_db_name="restored_novel.db"
            )

            self.assertTrue(os.path.isfile(restored_db_path))
            self.assertTrue(restored_db_path.endswith("restored_novel.db"))

            # 驗證還原出來的資料庫可被正常載入
            loaded = DatabaseService.load_project(restored_db_path)
            self.assertEqual(loaded.project_info.title, "備份測試專案")
            self.assertEqual(len(loaded.tree), 1)
            self.assertEqual(loaded.tree[0].content, "這是一段備份測試內容。")

    def test_backup_nonexistent_file_raises_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_db = os.path.join(tmpdir, "nonexistent.db")
            zip_path = os.path.join(tmpdir, "fail.zip")
            with self.assertRaises(FileNotFoundError):
                BackupService.create_backup(fake_db, zip_path)


if __name__ == "__main__":
    unittest.main()
