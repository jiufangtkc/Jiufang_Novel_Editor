import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication, QTreeWidgetItem
from PyQt6.QtCore import Qt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from views.main_window import MainWindow
from controllers.main_controller import MainController
from models.models import ChapterNode
from views.dialogs.import_preview_dialog import ImportPreviewDialog
from services.import_service import ImportOptions

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


class TestImportController(unittest.TestCase):
    """測試 ImportController、ImportPreviewDialog 與作品樹掛載邏輯。"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.view = MainWindow()
        self.mc = MainController(self.view)

    def tearDown(self):
        if hasattr(self.mc, 'writing_timer') and self.mc.writing_timer.isActive():
            self.mc.writing_timer.stop()
        if hasattr(self.mc, 'auto_save_timer') and self.mc.auto_save_timer.isActive():
            self.mc.auto_save_timer.stop()
        self.view.close()
        self.temp_dir.cleanup()

    def test_menu_actions_exist(self):
        """驗證主選單包含匯入動作，且設有 Ctrl+I 快速鍵。"""
        self.assertTrue(hasattr(self.view, "action_import"))
        self.assertEqual(self.view.action_import.shortcut().toString(), "Ctrl+I")

    def test_import_append_mode(self):
        """測試追加模式 (append)：節點順利掛載到作品樹末尾。"""
        initial_count = self.view.tree_widget.topLevelItemCount()

        nodes = [
            ChapterNode(
                name="第十卷 天下第一",
                node_type="folder",
                children=[
                    ChapterNode(
                        name="第一章 決鬥",
                        node_type="file",
                        content="這是決鬥的內容文字。"
                    )
                ]
            )
        ]

        with patch("PyQt6.QtWidgets.QMessageBox.information"):
            self.mc.import_controller._apply_imported_nodes(nodes, target_mode="append", target_item=None)

        # 頂層項目應增加 1
        new_count = self.view.tree_widget.topLevelItemCount()
        self.assertEqual(new_count, initial_count + 1)

        # 檢查新加入的項目
        last_item = self.view.tree_widget.topLevelItem(new_count - 1)
        self.assertEqual(last_item.text(0), "第十卷 天下第一")
        self.assertEqual(last_item.childCount(), 1)

        child_item = last_item.child(0)
        self.assertEqual(child_item.text(0), "第一章 決鬥")
        data = child_item.data(0, Qt.ItemDataRole.UserRole)
        self.assertEqual(data["content"], "這是決鬥的內容文字。")
        self.assertTrue(self.mc.is_dirty)

    def test_import_insert_mode_into_folder(self):
        """測試插入模式 (insert)：指定資料夾時，節點作為該資料夾的子項加入。"""
        folder_item = self.mc.tree.create_item("測試分卷", is_folder=True)
        self.view.tree_widget.addTopLevelItem(folder_item)

        nodes = [
            ChapterNode(
                name="第九章 潛入",
                node_type="file",
                content="夜黑風高。"
            )
        ]

        with patch("PyQt6.QtWidgets.QMessageBox.information"):
            self.mc.import_controller._apply_imported_nodes(nodes, target_mode="insert", target_item=folder_item)

        self.assertEqual(folder_item.childCount(), 1)
        child_item = folder_item.child(0)
        self.assertEqual(child_item.text(0), "第九章 潛入")

    def test_import_new_book_mode(self):
        """測試建立新書模式 (new_book)：清空舊有章節，全面替換為匯入的樹。"""
        nodes = [
            ChapterNode(
                name="卷一",
                node_type="folder",
                children=[
                    ChapterNode(name="第一回", node_type="file", content="開場白")
                ]
            )
        ]

        with patch("PyQt6.QtWidgets.QMessageBox.information"):
            self.mc.import_controller._apply_imported_nodes(nodes, target_mode="new_book", target_item=None)

        self.assertEqual(self.view.tree_widget.topLevelItemCount(), 1)
        root_item = self.view.tree_widget.topLevelItem(0)
        self.assertEqual(root_item.text(0), "卷一")
        self.assertEqual(root_item.child(0).text(0), "第一回")

    def test_dialog_filtering(self):
        """測試 ImportPreviewDialog 的節點過濾機制（反選特定項目）。"""
        dlg = ImportPreviewDialog(self.view)
        test_nodes = [
            ChapterNode(name="第一章", node_type="file", content="內文一"),
            ChapterNode(name="第二章", node_type="file", content="內文二"),
        ]
        dlg._populate_preview_tree(test_nodes)

        # 預設全部勾選
        selected = dlg.get_selected_nodes()
        self.assertEqual(len(selected), 2)

        # 取消勾選第一個項目
        item0 = dlg.tree_preview.topLevelItem(0)
        item0.setCheckState(0, Qt.CheckState.Unchecked)

        selected_after = dlg.get_selected_nodes()
        self.assertEqual(len(selected_after), 1)
        self.assertEqual(selected_after[0].name, "第二章")


if __name__ == "__main__":
    unittest.main()
