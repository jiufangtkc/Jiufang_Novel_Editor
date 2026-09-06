import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QTreeWidgetItem, QDialog, QMessageBox
from PyQt6.QtCore import Qt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.models import JneProject, ProjectInfo, ChapterNode
from views.main_window import MainWindow
from controllers.main_controller import MainController

app = QApplication.instance() or QApplication(sys.argv)


class TestP0BugFixes(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.view = MainWindow()
        self.mc = MainController(self.view)

    def tearDown(self):
        self.mc.writing_timer.stop()
        self.mc.auto_save_timer.stop()
        self.view.close()
        self.temp_dir.cleanup()



    def test_bug2_auto_format_dialog_skips_folder_type(self):
        """驗證全書自動排版對 folder 類型的節點不進行排版，僅排版 file 與 scene 節點。"""
        self.view.tree_widget.clear()

        # 建立資料夾節點（包含未縮排文字）
        folder_item = QTreeWidgetItem(["第一卷"])
        folder_item.setData(0, Qt.ItemDataRole.UserRole, {
            "id": "f-1",
            "name": "第一卷",
            "type": "folder",
            "content": "資料夾不應被縮排"
        })
        self.view.tree_widget.addTopLevelItem(folder_item)

        # 建立文章節點
        file_item = QTreeWidgetItem(["第一章"])
        file_item.setData(0, Qt.ItemDataRole.UserRole, {
            "id": "c-1",
            "name": "第一章",
            "type": "file",
            "content": "這是未縮排的第一行\n這是未縮排的第二行"
        })
        folder_item.addChild(file_item)

        # 建立場景節點
        scene_item = QTreeWidgetItem(["場景一"])
        scene_item.setData(0, Qt.ItemDataRole.UserRole, {
            "id": "s-1",
            "name": "場景一",
            "type": "scene",
            "content": "場景第一行\n場景第二行"
        })
        folder_item.addChild(scene_item)

        # 模擬呼叫 open_auto_format_dialog 內部邏輯
        with patch("views.dialogs.auto_format_dialog.AutoFormatDialog.exec", return_value=QDialog.DialogCode.Accepted), \
             patch("views.dialogs.auto_format_dialog.AutoFormatDialog.get_options", return_value={"scope": "all", "indent_mode": "indent"}), \
             patch("PyQt6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            self.mc.editor.open_auto_format_dialog()

        folder_data = folder_item.data(0, Qt.ItemDataRole.UserRole)
        file_data = file_item.data(0, Qt.ItemDataRole.UserRole)
        scene_data = scene_item.data(0, Qt.ItemDataRole.UserRole)

        # 資料夾內容應保持完全不變（未被排版）
        self.assertEqual(folder_data["content"], "資料夾不應被縮排")
        # 文章與場景應被自動排版（加上全形空格縮排）
        self.assertTrue(file_data["content"].startswith("　　"))
        self.assertTrue(scene_data["content"].startswith("　　"))

    def test_bug3_stats_controller_uses_project_save_temp_doc(self):
        """驗證 StatsController 內部所有暫存操作皆呼叫 self.mc.project.save_temp_doc()。"""
        self.mc.project.save_temp_doc = MagicMock()

        # 1. set_daily_target
        with patch("PyQt6.QtWidgets.QInputDialog.getInt", return_value=(3000, True)):
            self.mc.stats.set_daily_target()
        self.assertEqual(self.mc.project.save_temp_doc.call_count, 1)

        # 2. set_project_target
        with patch("PyQt6.QtWidgets.QInputDialog.getInt", return_value=(80000, True)):
            self.mc.stats.set_project_target()
        self.assertEqual(self.mc.project.save_temp_doc.call_count, 2)

        # 3. clear_daily_progress
        with patch("PyQt6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            self.mc.stats.clear_daily_progress()
        self.assertEqual(self.mc.project.save_temp_doc.call_count, 3)

        # 4. record_ai_activity
        self.mc.stats.record_ai_activity(continuation_count=1, feature_key="chat")
        self.assertEqual(self.mc.project.save_temp_doc.call_count, 4)


if __name__ == "__main__":
    unittest.main()
