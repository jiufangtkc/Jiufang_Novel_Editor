import os
from PyQt6.QtWidgets import QMessageBox, QInputDialog

from services.database import DatabaseService
from views.dialogs.snapshot_dialog import SnapshotDialog

class SnapshotController:
    """負責快照的建立、管理與還原。"""
    
    def __init__(self, main_controller):
        self.mc = main_controller

    @property
    def view(self):
        return self.mc.view

    def manage_snapshots(self):
        """開啟版本快照管理對話框。"""
        self.mc.save_current_editor_content()
        self.mc.project.save_temp_doc()

        db_path = self.mc.project.get_active_db_path()
        if not db_path:
            QMessageBox.warning(self.view, "提示", "尚未有任何專案資料庫可供管理快照。")
            return

        dialog = SnapshotDialog(self.view, db_path=db_path)
        dialog.btn_create.clicked.connect(lambda: self.create_snapshot(dialog))
        dialog.signal_restore_snapshot.connect(self.restore_snapshot)
        dialog.exec()

    def create_snapshot(self, dialog: SnapshotDialog = None):
        """彈出輸入名稱對話框並建立新快照。"""
        self.mc.save_current_editor_content()
        name, ok = QInputDialog.getText(
            dialog or self.view,
            "建立版本快照",
            "請輸入快照名稱（例如：第一版定稿、修稿前）："
        )
        if not ok:
            return
        name = name.strip() or "手動快照"

        note, ok_note = QInputDialog.getText(
            dialog or self.view,
            "快照備註",
            "請輸入備註說明（可留空）："
        )
        note = note.strip() if ok_note else ""

        db_path = self.mc.project.get_active_db_path()
        if not db_path:
            return

        project = self.mc.project._build_jne_project()
        try:
            snap_id = DatabaseService.save_snapshot(db_path, name, note, project)
            if dialog:
                dialog.refresh_snapshots()
            QMessageBox.information(self.view, "成功", f"已成功建立快照：「{name}」！")
        except Exception as e:
            QMessageBox.critical(self.view, "錯誤", f"建立快照失敗：{e}")

    def restore_snapshot(self, snapshot_id: int):
        """還原指定 ID 的快照。"""
        db_path = self.mc.project.get_active_db_path()
        if not db_path:
            return

        try:
            # 1. 還原前自動建立保護快照
            current_project = self.mc.project._build_jne_project()
            DatabaseService.save_snapshot(
                db_path,
                name="[系統自動保護] 還原前備份",
                note="由系統在執行快照還原前自動建立",
                project=current_project
            )

            # 2. 讀取目標快照
            target_project = DatabaseService.load_snapshot(db_path, snapshot_id)
            if not target_project:
                QMessageBox.warning(self.view, "還原失敗", "找不到該快照的資料內容。")
                return

            # 3. 載入至 UI 與狀態
            self.mc.project.load_project_data(target_project)

            # 4. 寫回資料庫與暫存
            DatabaseService.save_project(target_project, db_path)
            self.mc.project.save_temp_doc()

            QMessageBox.information(
                self.view,
                "還原成功",
                "專案已成功還原至所選快照狀態！\n（原狀態已自動存為保護快照）"
            )
        except Exception as e:
            QMessageBox.critical(self.view, "錯誤", f"還原快照時發生錯誤：{e}")
