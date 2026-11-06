from PyQt6.QtWidgets import QMessageBox
from services.ai_service import AIProofreadWorker
from views.dialogs.ai_settings_dialog import AISettingsDialog
from views.dialogs.ai_proofread_dialog import AIProofreadDialog


class AIController:
    """負責本機 AI 語意校稿與非同步背景任務之控制器。"""

    def __init__(self, main_controller):
        self.mc = main_controller
        self.view = main_controller.view
        self.proofread_worker = None
        self.proofread_dialog = None

    def open_ai_settings_dialog(self):
        """開啟 AI 助手設定對話框。"""
        dlg = AISettingsDialog(self.view)
        dlg.exec()

    def open_ai_proofread_dialog(self):
        """開啟 AI 校稿對話框。"""
        # 確保已儲存最新內容
        self.mc.editor.save_current_editor_content()
        self.mc.project.save_temp_doc()

        cursor = self.view.editor.textCursor()
        selected_text = cursor.selectedText().strip()
        target_text = selected_text if selected_text else self.view.editor.toPlainText().strip()

        if not target_text and not self.mc.tree.get_item_id(self.mc.current_file_item):
            QMessageBox.information(self.view, "提示", "目前編輯器內無文字，或尚未開啟章節可供 AI 校稿。")
            return

        if self.proofread_dialog is None:
            self.proofread_dialog = AIProofreadDialog(self.view, target_text)
            self.proofread_dialog.signal_navigate_to_match.connect(self.mc.search.navigate_to_global_match)
            self.proofread_dialog.signal_start_proofread.connect(self.handle_start_proofread)
            self.proofread_dialog.signal_change_status.connect(self.handle_proofread_status_change)
            self.proofread_dialog.signal_ignore_rule.connect(self.handle_proofread_ignore_rule)

        self.reload_proofread_results()
        self.proofread_dialog.show()
        self.proofread_dialog.raise_()
        self.proofread_dialog.activateWindow()

    def reload_proofread_results(self):
        from services.database import DatabaseService
        if self.proofread_dialog:
            db_path = self.mc.project.get_active_db_path()
            if db_path:
                results = DatabaseService.load_proofread_results(db_path)
                # 過濾掉 deleted 的結果
                active_results = [r for r in results if r["status"] != "deleted"]
                self.proofread_dialog.load_results(active_results)

    def handle_start_proofread(self, scope: str, options: dict):
        db_path = self.mc.project.get_active_db_path()
        if not db_path:
            QMessageBox.warning(self.view, "錯誤", "找不到專案資料庫路徑。")
            if self.proofread_dialog:
                self.proofread_dialog.finish_proofreading()
            return

        node_id = self.mc.tree.get_item_id(self.mc.current_file_item) if self.mc.current_file_item else ""
        chapter_name = self.mc.current_file_item.text(0) if self.mc.current_file_item else "未知章節"

        if scope == "目前選取文字":
            cursor = self.view.editor.textCursor()
            text = cursor.selectedText().replace("\u2029", "\n")
        else:
            text = self.view.editor.toPlainText()

        if not text.strip():
            QMessageBox.information(self.view, "提示", "目前校稿範圍無任何文字內容。")
            if self.proofread_dialog:
                self.proofread_dialog.finish_proofreading()
            return

        # 若前次校稿任務仍在執行，先主動取消
        if self.proofread_worker and self.proofread_worker.isRunning():
            self.proofread_worker.cancel()
            self.proofread_worker.wait(500)

        # 啟動非同步校稿背景執行緒
        self.proofread_worker = AIProofreadWorker(
            text_content=text,
            chapter_name=chapter_name,
            node_id=node_id,
            options=options
        )
        self.proofread_worker.progress_signal.connect(self._on_proofread_progress)
        self.proofread_worker.finished_signal.connect(self._on_proofread_finished)
        self.proofread_worker.error_signal.connect(self._on_proofread_error)
        self.proofread_worker.start()

    def _on_proofread_progress(self, current: int, total: int, message: str):
        if self.proofread_dialog and hasattr(self.proofread_dialog, "btn_start"):
            self.proofread_dialog.btn_start.setText(f"校稿中 ({current}/{total})...")

    def _on_proofread_finished(self, results: list):
        from services.database import DatabaseService
        db_path = self.mc.project.get_active_db_path()
        if db_path:
            # 讀取使用者設定之忽略規則清單並進行過濾
            ignored_rules = DatabaseService.load_ignored_rules(db_path)
            ignored_set = {(r.get("rule_type"), r.get("target_word")) for r in ignored_rules}

            for res in results:
                # 若吻合已忽略規則，略過不寫入資料庫
                if (res.get("category"), res.get("original_text")) in ignored_set:
                    continue
                DatabaseService.save_proofread_result(db_path, res)

            self.reload_proofread_results()

        if self.proofread_dialog:
            self.proofread_dialog.finish_proofreading()

        if hasattr(self.mc, "stats") and hasattr(self.mc.stats, "record_ai_activity"):
            self.mc.stats.record_ai_activity(chat_count=1, feature_key="proofread")

    def _on_proofread_error(self, error_message: str):
        if self.proofread_dialog:
            self.proofread_dialog.finish_proofreading()
        QMessageBox.warning(self.view, "AI 校稿失敗", f"AI 校稿執行失敗：\n{error_message}")

    def handle_proofread_status_change(self, result_id: str, new_status: str):
        from services.database import DatabaseService
        db_path = self.mc.project.get_active_db_path()
        if db_path:
            DatabaseService.update_proofread_result_status(db_path, result_id, new_status)
            self.reload_proofread_results()

    def handle_proofread_ignore_rule(self, category: str, original_text: str, result_id: str):
        from services.database import DatabaseService
        reply = QMessageBox.question(
            self.proofread_dialog,
            "確認忽略",
            f"這會讓 AI 校稿助手往後忽略「{original_text}」此校稿判斷，確定嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            db_path = self.mc.project.get_active_db_path()
            if db_path:
                DatabaseService.add_ignored_rule(db_path, category, original_text)
                DatabaseService.update_proofread_result_status(db_path, result_id, "ignored")
                self.reload_proofread_results()
