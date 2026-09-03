import os
import sys
import unittest
import tempfile
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from views.main_window import MainWindow
from controllers.main_controller import MainController
from services.database import DatabaseService


class TestSaveRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.view = MainWindow()
        self.mc = MainController(self.view)
        # 將儲存根路徑指向暫存目錄
        self.mc.app_settings["storage_path"] = self.temp_dir.name

    def tearDown(self):
        self.mc.writing_timer.stop()
        self.mc.auto_save_timer.stop()
        self.view.close()
        self.temp_dir.cleanup()

    def test_quiet_save_no_dialog(self):
        """測試快速存檔為安靜存檔，不彈出 QMessageBox.information，但在狀態列顯示訊息。"""
        self.mc.project_info.title = "安靜存檔測試"
        with patch.object(QMessageBox, "information") as mock_info:
            success = self.mc.save_project()
            self.assertTrue(success)
            mock_info.assert_not_called()

        status_msg = self.view.statusBar().currentMessage()
        self.assertIn("稿件已儲存至 安靜存檔測試.db", status_msg)

    def test_save_filename_uses_book_title_without_timestamp(self):
        """測試初次存檔依照書名命名，不再附加日期與時間戳。"""
        self.mc.project_info.title = "天外飛仙"
        success = self.mc.project.save_project()
        self.assertTrue(success)

        saved_path = self.mc.project.current_project_path
        self.assertTrue(os.path.exists(saved_path))
        filename = os.path.basename(saved_path)
        self.assertEqual(filename, "天外飛仙.db")

        # 驗證檔名不含時間戳
        import re
        self.assertIsNone(re.search(r'\d{8}_\d{6}', filename))

    def test_consecutive_save_overwrites_original_file(self):
        """測試連續存檔時使用本來的檔案名稱，不會產生多個時間戳檔案。"""
        self.mc.project_info.title = "單一存檔測試"
        self.mc.project.save_project()
        first_path = self.mc.project.current_project_path

        # 第二次存檔
        self.mc.project.save_project()
        second_path = self.mc.project.current_project_path

        self.assertEqual(first_path, second_path)
        book_dir = os.path.dirname(first_path)
        db_files = [f for f in os.listdir(book_dir) if f.endswith(".db")]
        self.assertEqual(len(db_files), 1)

    def test_save_retains_original_filename_even_if_book_title_changed(self):
        """測試存檔規則：除非另存新檔，否則存檔時使用本來的檔案名稱（即使書名被修改亦不重新命名）。"""
        self.mc.project_info.title = "原書名"
        self.mc.project.save_project()
        orig_path = self.mc.project.current_project_path
        self.assertTrue(orig_path.endswith("原書名.db"))

        # 修改書名，再次一般存檔
        self.mc.project_info.title = "已改之新書名"
        self.mc.project.save_project()

        # 仍舊使用本來的檔案名稱
        self.assertEqual(self.mc.project.current_project_path, orig_path)
        self.assertTrue(os.path.exists(orig_path))

    def test_save_project_as_updates_current_path_and_subsequent_saves(self):
        """測試另存新檔會更新為新路徑，且後續存檔使用新檔案名稱。"""
        self.mc.project_info.title = "另存測試"
        self.mc.project.save_project()
        orig_path = self.mc.project.current_project_path

        new_as_path = os.path.join(self.temp_dir.name, "另存副本.db")
        with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName', return_value=(new_as_path, "SQLite 資料庫 (*.db)")), \
             patch.object(QMessageBox, "information") as mock_info:
            success = self.mc.project.save_project_as()
            self.assertTrue(success)
            mock_info.assert_called_once()

        self.assertEqual(self.mc.project.current_project_path, new_as_path)
        self.assertTrue(os.path.exists(new_as_path))

        # 後續存檔沿用另存新檔後的路徑
        self.mc.project.save_project()
        self.assertEqual(self.mc.project.current_project_path, new_as_path)

    def test_ctrl_s_action_triggers_quiet_save(self):
        """測試透過 action_save_project（Ctrl+S 快捷鍵對應之動作）觸發時為安靜存檔。"""
        self.mc.project_info.title = "快捷鍵存檔"
        with patch.object(QMessageBox, "information") as mock_info:
            self.view.action_save_project.trigger()
            mock_info.assert_not_called()

        self.assertTrue(self.mc.project.current_project_path.endswith("快捷鍵存檔.db"))


if __name__ == '__main__':
    unittest.main()
