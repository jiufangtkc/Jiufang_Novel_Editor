import os
import re
import datetime
from PyQt6.QtWidgets import QMessageBox, QFileDialog

from services.backup_service import BackupService
from services.database import DatabaseService

class BackupController:
    """負責專案的 ZIP 備份與還原。"""
    
    def __init__(self, main_controller):
        self.mc = main_controller

    @property
    def view(self):
        return self.mc.view

    def export_backup_zip(self):
        """將專案資料庫打包為 ZIP 備份檔。"""
        self.mc.save_current_editor_content()
        self.mc.project.save_temp_doc()

        db_path = self.mc.project.get_active_db_path()
        if not db_path or not os.path.isfile(db_path):
            QMessageBox.warning(self.view, "提示", "尚未有已儲存的專案資料庫可供備份。")
            return

        book_title = getattr(self.mc.project_info, "title", "未命名專案") or "未命名專案"
        clean_title = re.sub(r'[\/\\\:\*\?\"\'<>\|]', '_', book_title)
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"{clean_title}_Backup_{now_str}.zip"

        backup_path, _ = QFileDialog.getSaveFileName(
            self.view,
            "匯出專案備份 (ZIP)",
            default_filename,
            "ZIP 壓縮備份 (*.zip *.jnebackup)"
        )
        if not backup_path:
            return

        try:
            BackupService.create_backup(
                project_db_path=db_path,
                backup_zip_path=backup_path,
                project_title=book_title,
                include_global_settings=True
            )
            QMessageBox.information(
                self.view,
                "備份成功",
                f"專案備份已成功建立至：\n{backup_path}"
            )
        except Exception as e:
            QMessageBox.critical(self.view, "備份失敗", f"建立備份時發生錯誤：{e}")

    def restore_from_backup_zip(self):
        """從 ZIP 備份檔還原專案。"""
        backup_path, _ = QFileDialog.getOpenFileName(
            self.view,
            "選擇專案備份檔",
            "",
            "ZIP 壓縮備份 (*.zip *.jnebackup)"
        )
        if not backup_path:
            return

        target_dir = self.mc.get_story_dir()
        try:
            restored_db_path = BackupService.restore_backup(backup_path, target_dir)
            project = DatabaseService.load_project(restored_db_path)
            self.mc.project.load_project_data(project)
            self.mc.project.current_project_path = restored_db_path
            self.mc.project.save_temp_doc()
            QMessageBox.information(
                self.view,
                "還原成功",
                f"專案已成功從備份中還原並載入！\n資料庫位置：{restored_db_path}"
            )
        except Exception as e:
            QMessageBox.critical(self.view, "還原失敗", f"從備份還原時發生錯誤：{e}")
