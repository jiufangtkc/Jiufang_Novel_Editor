import os
import sys
import tempfile
import unittest
from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtCore import Qt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from views.main_window import MainWindow
from views.dialogs.autosave_settings_dialog import AutosaveSettingsDialog
from views.dialogs.startup_dialog import StartupDialog
from services.app_settings_service import AppSettingsService, DEFAULT_WINDOW_SETTINGS
from services.database import DatabaseService
from models.models import JneProject, ProjectInfo, ChapterNode
from controllers.main_controller import MainController


class TestAutosaveAndStartup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

    def setUp(self):
        self.view = MainWindow()
        # 使用 interactive_startup=False 以免測試被彈出視窗阻塞
        self.mc = MainController(self.view, interactive_startup=False)

    def tearDown(self):
        self.mc.writing_timer.stop()
        self.mc.auto_save_timer.stop()
        self.view.close()

    def test_default_app_settings_fields(self):
        """測試偏好設定預設包含暫存頻率與上限等欄位。"""
        self.assertIn("autosave_interval_minutes", DEFAULT_WINDOW_SETTINGS)
        self.assertIn("autosave_max_files", DEFAULT_WINDOW_SETTINGS)
        self.assertIn("last_exit_normal", DEFAULT_WINDOW_SETTINGS)
        self.assertIn("session_active", DEFAULT_WINDOW_SETTINGS)
        self.assertIn("last_project_path", DEFAULT_WINDOW_SETTINGS)
        self.assertEqual(DEFAULT_WINDOW_SETTINGS["autosave_interval_minutes"], 10)
        self.assertEqual(DEFAULT_WINDOW_SETTINGS["autosave_max_files"], 100)

    def test_autosave_settings_dialog_ui(self):
        """測試 AutosaveSettingsDialog 的設定讀取與變更。"""
        dialog = AutosaveSettingsDialog(self.view, interval_minutes=15, max_files=50)
        self.assertEqual(dialog.spin_interval.value(), 15)
        self.assertEqual(dialog.spin_max_files.value(), 50)

        dialog.spin_interval.setValue(20)
        dialog.spin_max_files.setValue(80)
        interval, max_files = dialog.get_settings()
        self.assertEqual(interval, 20)
        self.assertEqual(max_files, 80)
        dialog.close()

    def test_startup_dialog_actions(self):
        """測試 StartupDialog 點擊開啟新專案與讀取專案存檔選項。"""
        dialog = StartupDialog(self.view)
        # 測試選擇 new
        dialog._on_new_clicked()
        self.assertEqual(dialog.selected_action, "new")

        # 測試選擇 open
        dialog._on_open_clicked()
        self.assertEqual(dialog.selected_action, "open")
        dialog.close()

    def test_autosave_timer_and_file_limit_cleanup(self):
        """測試暫存檔數量清理邏輯：超過上限時依時間由最舊的刪除。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 建立 5 個模擬暫存檔，名稱包含時間序
            file_names = [
                "temp_20260827_100000.db",
                "temp_20260827_101000.db",
                "temp_20260827_102000.db",
                "temp_20260827_103000.db",
                "temp_20260827_104000.db",
            ]
            for fname in file_names:
                fpath = os.path.join(temp_dir, fname)
                with open(fpath, "wb") as f:
                    f.write(b"dummy db data")

            # 設定上限為 3
            self.mc.project.clean_files_limit(temp_dir, limit=3)

            remaining_files = os.listdir(temp_dir)
            self.assertEqual(len(remaining_files), 3)
            # 應該保留最新的 3 個（102000, 103000, 104000）
            self.assertNotIn("temp_20260827_100000.db", remaining_files)
            self.assertNotIn("temp_20260827_101000.db", remaining_files)
            self.assertIn("temp_20260827_102000.db", remaining_files)
            self.assertIn("temp_20260827_103000.db", remaining_files)
            self.assertIn("temp_20260827_104000.db", remaining_files)

    def test_menu_action_autosave_settings_exists(self):
        """測試選單中已掛載 action_autosave_settings。"""
        self.assertIn("暫存與自動存檔設定", self.view.action_autosave_settings.text())

    def test_crash_recovery_trigger(self):
        """測試當前次標記為異常退出且存在暫存檔時，能正確載入最新暫存檔。"""
        # 建立一個測試用暫存資料夾與暫存檔
        temp_dir = os.path.join(self.mc.app_dir, "Temp_doc")
        os.makedirs(temp_dir, exist_ok=True)
        test_temp_db = os.path.join(temp_dir, "temp_20260827_999999.db")

        test_project = JneProject(
            project_info=ProjectInfo(title="當機恢復測試作品", logline="當機恢復測試大綱"),
            tree=[ChapterNode(name="測試第一卷", node_type="folder")]
        )
        DatabaseService.save_project(test_project, test_temp_db)

        try:
            # 建立另一個非互動的 MainController 模擬當機載入
            test_view = MainWindow()
            # 注入 crash 狀態
            settings_path = AppSettingsService.get_settings_file_path(self.mc.app_dir)
            saved_settings = AppSettingsService.load_settings(self.mc.app_dir)
            saved_settings["session_active"] = True
            saved_settings["last_exit_normal"] = False
            AppSettingsService.save_settings(saved_settings, self.mc.app_dir)

            test_mc = MainController(test_view, interactive_startup=False)
            # 驗證是否成功恢復暫存檔內容
            self.assertEqual(test_mc.project_info.title, "當機恢復測試作品")
            test_mc.writing_timer.stop()
            test_mc.auto_save_timer.stop()
            test_view.close()
        finally:
            if os.path.exists(test_temp_db):
                os.remove(test_temp_db)

    def test_startup_dialog_reject_sets_should_exit(self):
        """測試當作者在啟動視窗點擊 X 關閉時，控制器會標記 should_exit=True。"""
        from unittest.mock import patch, MagicMock
        saved_settings = AppSettingsService.load_settings(self.mc.app_dir)
        saved_settings["session_active"] = False
        saved_settings["last_exit_normal"] = True
        AppSettingsService.save_settings(saved_settings, self.mc.app_dir)

        test_view = MainWindow()
        mock_dlg = MagicMock()
        mock_dlg.exec.return_value = QDialog.DialogCode.Rejected
        with patch("controllers.main_controller.StartupDialog", return_value=mock_dlg):
            test_mc = MainController(test_view, interactive_startup=True)
            self.assertTrue(test_mc.should_exit)
            test_view.close()


if __name__ == "__main__":
    unittest.main()
