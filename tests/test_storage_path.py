import os
import sys
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.app_settings_service import AppSettingsService
from services.storage_migration_service import StorageMigrationService
from views.dialogs.storage_path_dialog import StoragePathDialog
from controllers.main_controller import MainController
from models.models import JneProject, ProjectInfo

app = QApplication.instance() or QApplication([])


class TestStoragePath(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app_dir = os.path.join(self.temp_dir.name, "app_data")
        os.makedirs(self.app_dir, exist_ok=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_app_settings_storage_path_helpers(self):
        """測試 AppSettingsService 的路徑輔助方法。"""
        # 1. 空設定回傳預設路徑
        settings = {"storage_path": ""}
        path = AppSettingsService.get_current_storage_path(settings, app_dir=self.app_dir)
        self.assertEqual(path, os.path.abspath(self.app_dir))

        # 2. 自訂路徑解析
        custom_path = os.path.join(self.temp_dir.name, "Custom_Sync")
        settings["storage_path"] = custom_path
        path = AppSettingsService.get_current_storage_path(settings, app_dir=self.app_dir)
        self.assertEqual(path, os.path.abspath(custom_path))

        # 3. get_story_dir 與 get_temp_dir
        story_dir = AppSettingsService.get_story_dir(custom_path)
        temp_dir = AppSettingsService.get_temp_dir(custom_path)
        self.assertEqual(story_dir, os.path.join(custom_path, "Story"))
        self.assertEqual(temp_dir, os.path.join(custom_path, "Temp_doc"))

        # 4. 相容已存在的小寫 story 目錄
        lower_story = os.path.join(custom_path, "story")
        os.makedirs(lower_story, exist_ok=True)
        self.assertEqual(AppSettingsService.get_story_dir(custom_path), lower_story)

    def test_storage_migration_service_ensure_directories(self):
        """測試 StorageMigrationService.ensure_storage_directories 能自動建立 Story 與 Temp_doc。"""
        target = os.path.join(self.temp_dir.name, "MyDropbox")
        story_dir, temp_dir = StorageMigrationService.ensure_storage_directories(target)

        self.assertTrue(os.path.exists(story_dir))
        self.assertTrue(os.path.exists(temp_dir))
        self.assertTrue(os.path.isdir(story_dir))
        self.assertTrue(os.path.isdir(temp_dir))
        self.assertEqual(os.path.basename(story_dir), "Story")
        self.assertEqual(os.path.basename(temp_dir), "Temp_doc")

    def test_storage_migration_service_is_valid_writable_dir(self):
        """測試目錄可寫入性檢測。"""
        valid_dir = os.path.join(self.temp_dir.name, "WritableDir")
        self.assertTrue(StorageMigrationService.is_valid_writable_dir(valid_dir))
        self.assertFalse(StorageMigrationService.is_valid_writable_dir(""))

    def test_storage_migration_service_data_migration(self):
        """測試將舊目錄之稿件與暫存檔完整遷移至新目錄。"""
        old_root = os.path.join(self.temp_dir.name, "OldRoot")
        new_root = os.path.join(self.temp_dir.name, "NewRoot")

        # 建立舊目錄與假資料
        old_story, old_temp = StorageMigrationService.ensure_storage_directories(old_root)
        book1_dir = os.path.join(old_story, "仙俠修真傳")
        os.makedirs(book1_dir, exist_ok=True)
        file1 = os.path.join(book1_dir, "仙俠修真傳_20260831.db")
        with open(file1, "w", encoding="utf-8") as f:
            f.write("dummy db content 1")

        temp_file1 = os.path.join(old_temp, "temp_20260831_120000.db")
        with open(temp_file1, "w", encoding="utf-8") as f:
            f.write("dummy temp content 1")

        # 執行遷移
        result = StorageMigrationService.migrate_storage_data(old_root, new_root)
        self.assertEqual(result["story_files_copied"], 1)
        self.assertEqual(result["temp_files_copied"], 1)
        self.assertEqual(len(result["errors"]), 0)

        # 驗證新路徑檔案存在且內容正確
        new_file1 = os.path.join(new_root, "Story", "仙俠修真傳", "仙俠修真傳_20260831.db")
        new_temp_file1 = os.path.join(new_root, "Temp_doc", "temp_20260831_120000.db")
        self.assertTrue(os.path.exists(new_file1))
        self.assertTrue(os.path.exists(new_temp_file1))
        with open(new_file1, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "dummy db content 1")

    def test_storage_path_dialog_ui(self):
        """測試 StoragePathDialog 介面操作與預設還原。"""
        dlg = StoragePathDialog(current_path="C:\\MyCloud\\Jiufang")
        self.assertEqual(dlg.get_selected_storage_path(), "C:\\MyCloud\\Jiufang")

        # 點擊恢復預設
        dlg._reset_to_default()
        self.assertEqual(dlg.get_selected_storage_path(), AppSettingsService.get_default_storage_path())

    def test_project_controller_open_storage_path_dialog_flow(self):
        """測試從 ProjectController 觸發存檔路徑切換並驗證專案儲存路徑重定位。"""
        from views.main_window import MainWindow
        view = MainWindow()
        with patch.object(MainController, '_handle_startup_choice', lambda self: None):
            mc = MainController(view=view, interactive_startup=False)
            mc.app_dir = self.app_dir
            mc.app_settings = AppSettingsService.load_settings(self.app_dir)
            StorageMigrationService.ensure_storage_directories(mc.get_storage_path())

            old_path = mc.get_storage_path()
            self.assertTrue(os.path.exists(mc.get_story_dir()))
            self.assertTrue(os.path.exists(mc.get_temp_dir()))

            # 模擬先存一個稿件
            mc.project_info.title = "星際冒險"
            mc.project.save_project()
            orig_saved_path = mc.project.current_project_path
            self.assertTrue(os.path.exists(orig_saved_path))

            # 模擬使用者開啟 StoragePathDialog 並選取新路徑
            new_storage = os.path.join(self.temp_dir.name, "OneDrive_Novel")

            with patch('views.dialogs.storage_path_dialog.StoragePathDialog.exec', return_value=QDialog.DialogCode.Accepted), \
                 patch('views.dialogs.storage_path_dialog.StoragePathDialog.get_selected_storage_path', return_value=new_storage), \
                 patch('PyQt6.QtWidgets.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes), \
                 patch('PyQt6.QtWidgets.QMessageBox.information'):
                mc.project.open_storage_path_dialog()

            # 驗證存檔路徑已更新
            self.assertEqual(mc.app_settings.get("storage_path"), os.path.abspath(new_storage))
            self.assertEqual(mc.get_storage_path(), os.path.abspath(new_storage))
            self.assertTrue(os.path.exists(os.path.join(new_storage, "Story")))
            self.assertTrue(os.path.exists(os.path.join(new_storage, "Temp_doc")))

            # 驗證原稿件已遷移至新目錄
            migrated_file = os.path.join(new_storage, "Story", "星際冒險", os.path.basename(orig_saved_path))
            self.assertTrue(os.path.exists(migrated_file))

            # 驗證 current_project_path 自動重定位
            self.assertEqual(mc.project.current_project_path, migrated_file)

            # 後續存檔也自動寫入新路徑
            mc.project.save_temp_doc()
            new_temp_files = os.listdir(os.path.join(new_storage, "Temp_doc"))
            self.assertTrue(any(f.endswith(".db") for f in new_temp_files))


if __name__ == '__main__':
    unittest.main()
