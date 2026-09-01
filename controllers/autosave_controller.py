import os
import sys
import datetime
from typing import Optional
from PyQt6.QtWidgets import QMessageBox, QDialog
from PyQt6.QtCore import QTimer

from services.database import DatabaseService
from services.app_settings_service import AppSettingsService
from views.dialogs.autosave_settings_dialog import AutosaveSettingsDialog
from utils.file_utils import get_temp_db_sort_key

class AutosaveController:
    """負責自動暫存 (Autosave)、暫存檔清理 (Cleanup)、崩潰還原 (Crash Recovery) 與排程計時器管理。"""

    def __init__(self, main_controller):
        self.mc = main_controller

    @property
    def view(self):
        return self.mc.view

    def clean_files_limit(self, folder_path: str, limit: Optional[int] = None):
        """清理資料夾內多餘檔案，依照時間戳排序僅保留最近的 limit 個檔案。"""
        if limit is None:
            limit = getattr(self.mc, "autosave_max_files", 100)
        if not os.path.exists(folder_path):
            return
        try:
            files = [os.path.join(folder_path, f) for f in os.listdir(folder_path)]
            files = [f for f in files if os.path.isfile(f)]
            if len(files) > limit:
                files.sort(key=get_temp_db_sort_key)
                delete_count = len(files) - limit
                for i in range(delete_count):
                    try:
                        os.remove(files[i])
                    except Exception:
                        pass
        except Exception:
            pass

    def save_temp_doc(self):
        """將當前專案狀態即時暫存至 Temp_doc 目錄下的 SQLite .db 格式。"""
        self.mc.flush_active_writing_session()
        try:
            temp_dir = self.mc.get_temp_dir()
            os.makedirs(temp_dir, exist_ok=True)

            project = self.mc.project._build_jne_project()
            now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_file_name = f"temp_{now_str}.db"
            temp_file_path = os.path.join(temp_dir, temp_file_name)

            DatabaseService.save_project(project, temp_file_path)
            max_files = getattr(self.mc, "autosave_max_files", 100)
            self.clean_files_limit(temp_dir, limit=max_files)
        except Exception as e:
            print(f"暫存失敗: {e}", file=sys.stderr)

    def auto_load_latest_temp(self) -> bool:
        """軟體啟動或崩潰還原時自動檢查 Temp_doc 與存檔目錄，並優先載入最新暫存檔。"""
        temp_dir = self.mc.get_temp_dir()

        # 1. 優先檢查 Temp_doc 下的 .db 暫存檔
        if os.path.exists(temp_dir):
            db_files = [
                os.path.join(temp_dir, f) for f in os.listdir(temp_dir)
                if f.lower().endswith(".db") and os.path.isfile(os.path.join(temp_dir, f))
            ]
            db_files = [f for f in db_files if os.path.getsize(f) > 0]
            if db_files:
                db_files.sort(key=get_temp_db_sort_key, reverse=True)
                for db_file in db_files:
                    try:
                        loaded_project = DatabaseService.load_project(db_file)
                        if loaded_project and (loaded_project.tree or (loaded_project.project_info and loaded_project.project_info.title)):
                            self.mc.project.load_project_data(loaded_project)
                            return True
                    except Exception as e:
                        print(f"嘗試載入暫存檔 {db_file} 失敗: {e}", file=sys.stderr)

            # 2. 若無可用 .db 檔案，檢查是否有舊版 .json 暫存檔
            json_files = [
                os.path.join(temp_dir, f) for f in os.listdir(temp_dir)
                if f.lower().endswith(".json") and os.path.isfile(os.path.join(temp_dir, f))
            ]
            json_files = [f for f in json_files if os.path.getsize(f) > 0]
            if json_files:
                json_files.sort(key=get_temp_db_sort_key, reverse=True)
                for json_file in json_files:
                    try:
                        from services.storage import StorageService
                        data = StorageService.load_data(json_file)
                        if data:
                            self.mc.project.load_project_data(data)
                            return True
                    except Exception as e:
                        print(f"嘗試載入舊版 JSON 暫存檔 {json_file} 失敗: {e}", file=sys.stderr)

        # 3. 若 Temp_doc 無可用暫存檔，檢查 story/ 正式存檔目錄作為保底
        story_dir = self.mc.get_story_dir()
        if os.path.exists(story_dir):
            story_files = []
            for root, _, files in os.walk(story_dir):
                for f in files:
                    if f.lower().endswith(".db"):
                        full_p = os.path.join(root, f)
                        if os.path.isfile(full_p) and os.path.getsize(full_p) > 0:
                            story_files.append(full_p)
            if story_files:
                story_files.sort(key=get_temp_db_sort_key, reverse=True)
                for s_file in story_files:
                    try:
                        loaded_project = DatabaseService.load_project(s_file)
                        if loaded_project:
                            self.mc.project.load_project_data(loaded_project)
                            self.mc.project.current_project_path = s_file
                            return True
                    except Exception as e:
                        print(f"嘗試載入正式存檔 {s_file} 失敗: {e}", file=sys.stderr)

        return False

    def open_autosave_settings_dialog(self):
        """開啟暫存與自動存檔設定對話框。"""
        curr_interval = getattr(self.mc, "autosave_interval_minutes", 10)
        curr_max_files = getattr(self.mc, "autosave_max_files", 100)

        dialog = AutosaveSettingsDialog(self.view, interval_minutes=curr_interval, max_files=curr_max_files)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            interval, max_files = dialog.get_settings()
            self.mc.autosave_interval_minutes = interval
            self.mc.autosave_max_files = max_files
            if hasattr(self.mc, 'auto_save_timer') and self.mc.auto_save_timer:
                self.mc.auto_save_timer.setInterval(interval * 60 * 1000)

            # 更新並儲存偏好設定
            self.mc.app_settings["autosave_interval_minutes"] = interval
            self.mc.app_settings["autosave_max_files"] = max_files
            AppSettingsService.save_settings(self.mc.app_settings, self.mc.app_dir)

            # 立即執行一次清理上限檢查
            temp_dir = self.mc.get_temp_dir()
            self.clean_files_limit(temp_dir, limit=max_files)

            QMessageBox.information(
                self.view,
                "設定成功",
                f"暫存與自動存檔設定已更新！\n\n• 自動存檔間隔：{interval} 分鐘\n• 最多保留暫存檔：{max_files} 個"
            )
