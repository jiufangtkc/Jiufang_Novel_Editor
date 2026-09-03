import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from views.main_window import MainWindow
from controllers.main_controller import MainController


class TestUnsavedChanges(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.view = MainWindow()
        self.mc = MainController(self.view, interactive_startup=False, app_dir=self.temp_dir.name)

    def tearDown(self):
        self.mc.interactive_startup = False
        self.mc.mark_dirty(False)
        self.mc.writing_timer.stop()
        self.mc.auto_save_timer.stop()
        self.view.close()
        self.temp_dir.cleanup()

    def test_initial_state_clean(self):
        """測試全新專案初始化後，未存檔狀態為 False 且視窗標題不含星號。"""
        self.assertFalse(self.mc.is_dirty)
        self.assertNotIn(" *", self.view.windowTitle())

    def test_editor_text_change_marks_dirty(self):
        """測試在編輯器內輸入文字，觸發 mark_dirty(True) 且視窗標題帶星號。"""
        # 選取第一幕開始編輯
        item = self.view.tree_widget.topLevelItem(0).child(0).child(0)
        self.mc.tree.on_tree_item_clicked(item, 0)
        self.mc.mark_dirty(False)

        # 模擬作家打字
        self.view.editor.insertPlainText("測試新段落")
        self.assertTrue(self.mc.is_dirty)
        self.assertIn(" *", self.view.windowTitle())

    def test_save_project_clears_dirty(self):
        """測試執行正式存檔成功後，is_dirty 恢復為 False 且星號消失。"""
        self.mc.mark_dirty(True)
        self.assertTrue(self.mc.is_dirty)
        self.assertIn(" *", self.view.windowTitle())

        # 執行靜默存檔
        with patch("services.database.DatabaseService.save_project"):
            success = self.mc.save_project(silent=True)
            self.assertTrue(success)
            self.assertFalse(self.mc.is_dirty)
            self.assertNotIn(" *", self.view.windowTitle())

    def test_tree_node_change_marks_dirty(self):
        """測試章節樹重新命名或結構異動時，會自動標記 is_dirty。"""
        self.mc.mark_dirty(False)
        item = self.view.tree_widget.topLevelItem(0)
        with patch("PyQt6.QtWidgets.QInputDialog.getText", return_value=("第二卷", True)):
            self.mc.tree.rename_tree_node(item)
        self.assertTrue(self.mc.is_dirty)

    def test_on_close_event_when_clean(self):
        """測試無未儲存變更時，關閉事件直接 accept，不彈出對話框。"""
        self.mc.interactive_startup = True
        self.mc.mark_dirty(False)

        mock_event = MagicMock()
        with patch.object(self.mc.project, "prompt_save_changes_dialog") as mock_prompt:
            self.mc.project.on_close_event(mock_event)
            mock_prompt.assert_not_called()
            mock_event.accept.assert_called_once()
            mock_event.ignore.assert_not_called()

    def test_on_close_event_save_choice(self):
        """測試有變更時關閉，作家選擇「儲存」，執行存檔並 accept 關閉。"""
        self.mc.interactive_startup = True
        self.mc.mark_dirty(True)

        mock_event = MagicMock()
        with patch.object(self.mc.project, "prompt_save_changes_dialog", return_value="save") as mock_prompt:
            with patch.object(self.mc.project, "save_project", return_value=True) as mock_save:
                self.mc.project.on_close_event(mock_event)
                mock_prompt.assert_called_once()
                mock_save.assert_called_once_with(silent=True)
                mock_event.accept.assert_called_once()
                mock_event.ignore.assert_not_called()

    def test_on_close_event_discard_choice(self):
        """測試有變更時關閉，作家選擇「不儲存」，不執行正式存檔且不更新 temp_doc，直接 accept 關閉。"""
        self.mc.interactive_startup = True
        self.mc.mark_dirty(True)

        mock_event = MagicMock()
        with patch.object(self.mc.project, "prompt_save_changes_dialog", return_value="discard") as mock_prompt:
            with patch.object(self.mc.project, "save_project") as mock_save:
                with patch.object(self.mc.project, "save_temp_doc") as mock_temp:
                    self.mc.project.on_close_event(mock_event)
                    mock_prompt.assert_called_once()
                    mock_save.assert_not_called()
                    mock_temp.assert_not_called()
                    mock_event.accept.assert_called_once()
                    mock_event.ignore.assert_not_called()

    def test_on_close_event_cancel_choice(self):
        """測試有變更時關閉，作家選擇「取消」，呼叫 ignore 取消關閉，留在編輯器。"""
        self.mc.interactive_startup = True
        self.mc.mark_dirty(True)

        mock_event = MagicMock()
        with patch.object(self.mc.project, "prompt_save_changes_dialog", return_value="cancel") as mock_prompt:
            with patch.object(self.mc.project, "save_project") as mock_save:
                self.mc.project.on_close_event(mock_event)
                mock_prompt.assert_called_once()
                mock_save.assert_not_called()
                mock_event.ignore.assert_called_once()
                mock_event.accept.assert_not_called()

    def test_on_close_event_save_failed_ignores_close(self):
        """測試有變更時選擇儲存，但存檔失敗時，呼叫 ignore 阻止關閉以保護資料。"""
        self.mc.interactive_startup = True
        self.mc.mark_dirty(True)

        mock_event = MagicMock()
        with patch.object(self.mc.project, "prompt_save_changes_dialog", return_value="save") as mock_prompt:
            with patch.object(self.mc.project, "save_project", return_value=False) as mock_save:
                self.mc.project.on_close_event(mock_event)
                mock_prompt.assert_called_once()
                mock_save.assert_called_once_with(silent=True)
                mock_event.ignore.assert_called_once()
                mock_event.accept.assert_not_called()
