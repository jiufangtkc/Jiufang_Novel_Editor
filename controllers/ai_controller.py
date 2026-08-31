from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.QtGui import QTextCursor
from services.ai_service import AIService, AIWorker, AIContinuationWorker, AIStreamWorker
from views.dialogs.ai_settings_dialog import AISettingsDialog
from views.dialogs.ai_preview_dialog import AIPreviewDialog
from views.dialogs.ai_chat_dialog import AIChatDialog
from views.dialogs.ai_expansion_dialog import AIExpansionDialog
from views.dialogs.ai_proofread_dialog import AIProofreadDialog
from views.dialogs.ai_scope_dialog import AIScopeDialog
from views.dialogs.ai_character_review_dialog import AICharacterReviewDialog
from views.components.ai_task_overlay import AITaskOverlay
from views.components.ai_floating_hud import AIFloatingHUD


class AIController:
    """負責 AI 輔助分析、多輪對話、智慧續寫、卡片生成與非同步背景任務之控制器。"""

    def __init__(self, main_controller):
        self.mc = main_controller
        self.view = main_controller.view
        self.ai_worker = None
        self.continuation_worker = None
        self.stream_worker = None
        self.ai_task_overlay = None
        self.ai_floating_hud = None
        self.proofread_dialog = None

    def open_ai_settings_dialog(self):
        """開啟 AI 助手設定對話框。"""
        dlg = AISettingsDialog(self.view)
        dlg.exec()
        
    def open_ai_proofread_dialog(self):
        """開啟 AI 校稿對話框。"""
        # 確保已儲存最新內容
        self.mc.save_current_editor_content()
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
        from services.database import DatabaseService
        import uuid
        import datetime
        
        db_path = self.mc.project.get_active_db_path()
        if not db_path:
            QMessageBox.warning(self.view, "錯誤", "找不到專案資料庫路徑。")
            self.proofread_dialog.finish_proofreading()
            return
            
        node_id = self.mc.tree.get_item_id(self.mc.current_file_item)
        chapter_name = self.mc.current_file_item.text(0) if self.mc.current_file_item else "未知章節"
        text = self.view.editor.toPlainText()
        
        # 模擬產生假資料 (以展示 UI 和導航功能)
        words_to_find = []
        if options.get("typo"): words_to_find.append(("的", "typo", "得"))
        if options.get("usage"): words_to_find.append(("十分", "usage", "非常"))
        if options.get("suggestion"): words_to_find.append(("然後", "suggestion", "接著"))
        
        for word, cat, sugg in words_to_find:
            idx = text.find(word)
            if idx != -1:
                res = {
                    "id": str(uuid.uuid4()),
                    "category": cat,
                    "node_id": node_id,
                    "chapter_name": chapter_name,
                    "char_offset": idx,
                    "match_len": len(word),
                    "original_text": word,
                    "suggestion": sugg,
                    "reason": "AI 模擬檢查出的問題",
                    "status": "pending",
                    "created_at": datetime.datetime.now().isoformat()
                }
                DatabaseService.save_proofread_result(db_path, res)
                
        self.reload_proofread_results()
        self.proofread_dialog.finish_proofreading()
        
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

    def open_ai_chat_dialog(self, context_text: str = ""):
        """開啟 AI 多輪對話對話框（可帶入選取或指定之上下文）。"""
        if not context_text:
            cursor = self.view.editor.textCursor()
            selected = cursor.selectedText().strip()
            if selected:
                context_text = selected

        dlg = AIChatDialog(self.view, initial_context=context_text)
        dlg.signal_insert_to_editor.connect(self.insert_text_to_editor)
        dlg.signal_save_as_card.connect(lambda title, content: self.add_card_from_ai("summary", title, content))
        if hasattr(self.mc, 'stats') and hasattr(self.mc.stats, 'record_ai_activity'):
            self.mc.stats.record_ai_activity(chat_count=1)
        dlg.exec()

    def insert_text_to_editor(self, text: str):
        """將文字插入至當前主編輯器游標位置。"""
        cursor = self.view.editor.textCursor()
        cursor.insertText(text)
        self.view.editor.setTextCursor(cursor)
        self.view.editor.ensureCursorVisible()
        self.mc.update_status_bar()
        self.mc.save_temp_doc()

    def handle_editor_ai_analyze(self, task_type: str, text: str):
        """處理編輯器右鍵或選單觸發的 AI 分析。"""
        if task_type == "character":
            self.mc.save_current_editor_content()
            dlg = AIScopeDialog(self.view, current_item=self.mc.current_file_item, selected_text=text)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                scope_data = dlg.get_scope_content()
                self.start_ai_analysis(task_type, scope_data["text_content"], scope_data["scope_title"])
            return

        chapter_title = self.mc.current_file_item.text(0) if self.mc.current_file_item else ""
        self.start_ai_analysis(task_type, text, chapter_title)

    def trigger_ai_analysis(self, task_type: str):
        """從工具列或選單觸發 AI 分析。"""
        cursor = self.view.editor.textCursor()
        selected_text = cursor.selectedText().strip()

        # 登場角色提取：彈出專屬範圍選擇對話框（可選全文、當前章節、部分章節）
        if task_type == "character":
            self.mc.save_current_editor_content()
            dlg = AIScopeDialog(self.view, current_item=self.mc.current_file_item, selected_text=selected_text)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                scope_data = dlg.get_scope_content()
                self.start_ai_analysis(task_type, scope_data["text_content"], scope_data["scope_title"])
            return

        target_text = selected_text if selected_text else self.view.editor.toPlainText().strip()
        if not target_text:
            QMessageBox.information(self.view, "提示", "目前編輯器內無文字可供 AI 分析。")
            return

        chapter_title = self.mc.current_file_item.text(0) if self.mc.current_file_item else ""
        self.start_ai_analysis(task_type, target_text, chapter_title)

    def start_ai_analysis(self, task_type: str, text: str, chapter_title: str = ""):
        """啟動非同步 AI 分析執行緒，並展示無焦點浮動進度 HUD。"""
        if self.ai_worker and self.ai_worker.isRunning():
            QMessageBox.warning(self.view, "提示", "AI 分析進行中，請稍候完成後再發起新請求。")
            return

        if not self.ai_floating_hud:
            self.ai_floating_hud = AIFloatingHUD(self.view)
            self.ai_floating_hud.signal_cancel.connect(self.cancel_ai_analysis)

        task_name_map = {
            "character": "👤 登場角色提取",
            "impression": "📝 文學評語與寫作建議",
            "world": "🌍 世界觀設定提取",
            "timeline": "⏱️ 時間線與事件梳理"
        }
        t_name = task_name_map.get(task_type, "✨ AI 文本分析")
        if chapter_title:
            t_name = f"{t_name} — {chapter_title}"
        self.ai_floating_hud.start(t_name)

        self.ai_worker = AIWorker(task_type, text, chapter_title=chapter_title)
        self.ai_worker.progress_signal.connect(self.on_ai_analysis_progress)
        self.ai_worker.finished_signal.connect(self.on_ai_analysis_finished)
        self.ai_worker.error_signal.connect(self.on_ai_analysis_error)
        self.ai_worker.start()

    def cancel_ai_analysis(self):
        """取消正在進行中的 AI 分析背景任務。"""
        if self.ai_worker and self.ai_worker.isRunning():
            self.ai_worker.cancel()
            self.ai_worker.terminate()
            self.mc.update_status_bar()

    def on_ai_analysis_progress(self, current: int, total: int, message: str):
        """AI 分析進度回報更新至浮動 HUD。"""
        if self.ai_floating_hud:
            self.ai_floating_hud.update_progress(current, total, message)

    def on_ai_analysis_finished(self, result_data: dict):
        """AI 分析成功回傳後的處理流程。"""
        if self.ai_floating_hud:
            self.ai_floating_hud.finish("✅ 分析完成！")
        self.mc.update_status_bar()

        if hasattr(self.mc, 'stats') and hasattr(self.mc.stats, 'record_ai_activity'):
            self.mc.stats.record_ai_activity(chat_count=1)

        task_type = result_data.get("task_type", "")
        if task_type == "character":
            # 角色提取：開啟多角色卡與關係卡審核對話框
            dlg = AICharacterReviewDialog(self.view, result_data)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                cards = dlg.get_selected_cards()
                for c in cards:
                    self.add_card_from_ai(
                        category=c["category"],
                        title=c["title"],
                        content=c["content"],
                        summary=c.get("summary", ""),
                        tags=c.get("tags", [])
                    )
                QMessageBox.information(self.view, "成功", f"已成功建立 {len(cards)} 張角色卡片與關係卡至資料集！")
        else:
            # 其他一般分析：開啟單卡審核對話框
            dlg = AIPreviewDialog(self.view, result_data)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                card_info = dlg.get_card_data()
                self.add_card_from_ai(
                    category=card_info["category"],
                    title=card_info["title"],
                    content=card_info["content"],
                    summary=card_info["summary"],
                    tags=card_info["tags"]
                )
                QMessageBox.information(self.view, "成功", f"已成功建立卡片「{card_info['title']}」至資料集！")

    def on_ai_analysis_error(self, err_msg: str):
        """AI 分析發生錯誤時的回報與導引。"""
        if self.ai_floating_hud:
            self.ai_floating_hud.set_error(err_msg)
        self.mc.update_status_bar()
        reply = QMessageBox.critical(
            self.view,
            "AI 分析失敗",
            f"呼叫 AI 服務時發生錯誤：\n\n{err_msg}\n\n是否開啟 AI 助手設定以檢查 API 金鑰與連線設定？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.open_ai_settings_dialog()

    def trigger_ai_continuation(self):
        """觸發 AI 智慧擴寫（含安全開關檢查）。"""
        settings = AIService.load_settings()
        if not settings.get("ai_continuation_enabled", False):
            reply = QMessageBox.question(
                self.view,
                "AI 擴寫未啟用",
                "AI 智慧擴寫功能目前尚未啟用。\n\n本功能預設關閉以維護創作自主性。是否前往「AI 助手設定」檢閱並開啟此功能？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.open_ai_settings_dialog()
            return

        if self.stream_worker and self.stream_worker.isRunning():
            QMessageBox.warning(self.view, "提示", "AI 擴寫生成中，請稍候...")
            return

        dlg = AIExpansionDialog(self.view)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_expansion_data()
            self._start_ai_expansion(data)

    def _start_ai_expansion(self, data: dict):
        if not self.ai_task_overlay:
            self.ai_task_overlay = AITaskOverlay(self.view, title="✨ AI 擴寫任務")
            self.ai_task_overlay.signal_insert_text.connect(self._insert_streamed_text)
        
        preceding = data.get("preceding", "")
        succeeding = data.get("succeeding", "")
        guideline = data.get("guideline", "")
        word_count = data.get("word_count", 500)
        
        user_content = ""
        if preceding:
            user_content += f"【前文】\n{preceding}\n\n"
        if succeeding:
            user_content += f"【後文】\n{succeeding}\n\n"
        if guideline:
            user_content += f"【擴寫指引】\n{guideline}\n\n"
            
        user_content += f"【任務要求】\n請根據上方資訊，進行小說正文擴寫。預期擴寫長度約為 {word_count} 字。請直接輸出擴寫內容，不要包含任何開場白、問候語、解釋或標題。"

        settings = AIService.load_settings()
        system_prompt = settings.get("prompts", {}).get("continuation", "")

        self.ai_task_overlay.start_task()
        self.ai_task_overlay.set_status("thinking") # 進入思考狀態
        
        # 由於 stream_worker 的 API 我們沒有在 call_api_stream 裡做真正連線前區分「理解」與「思考」，
        # 因此這邊將 UI 第一步視作思考中，直到第一字元傳回。
        
        self.stream_worker = AIStreamWorker(system_prompt, user_content)
        self.stream_worker.first_token_signal.connect(lambda: self.ai_task_overlay.set_status("working"))
        self.stream_worker.chunk_received_signal.connect(self.ai_task_overlay.append_chunk)
        self.stream_worker.finished_signal.connect(self._on_expansion_finished)
        self.stream_worker.error_signal.connect(self._on_expansion_error)
        self.stream_worker.start()

    def _on_expansion_finished(self, full_text: str):
        self.ai_task_overlay.finish_task()
        if hasattr(self.mc, 'stats') and hasattr(self.mc.stats, 'record_ai_activity'):
            self.mc.stats.record_ai_activity(continuation_count=1, continuation_chars=len(full_text))
            self.mc.update_status_bar()

    def _on_expansion_error(self, err_msg: str):
        self.ai_task_overlay.error_task(err_msg)

    def _insert_streamed_text(self, text: str):
        self.insert_text_to_editor(text)
        self.ai_task_overlay.close()

    def add_card_from_ai(self, category: str, title: str, content: str, summary: str = "", tags: list = None):
        """將 AI 生成的資料新增為資料集卡片（Data-driven，直接操作 CardNode）。"""
        from models.models import CardNode, BUILTIN_CATEGORIES

        # 若分類不存在，退回 summary
        if category not in self.mc.project_cards:
            category = "summary"

        final_content = content
        if tags:
            tag_str = " ".join([f"#{t}" for t in tags])
            if tag_str:
                final_content = f"【標籤】{tag_str}\n\n{final_content}"

        new_card = CardNode(
            title=title,
            content=final_content,
            color="#2d4a6e"  # AI 生成卡片使用偏藍色區分
        )
        self.mc.project_cards[category].append(new_card)
        self.mc.card.rebuild_card_tree()
        self.mc.save_temp_doc()

        # 在樹狀導航中選中並滾動到新卡片
        new_item = self.mc.card._find_tree_item_by_id(new_card.id)
        if new_item:
            self.mc.card.card_tree.scrollToItem(new_item)
            self.mc.card.card_tree.setCurrentItem(new_item)

        # 若右側面板收折，展開它
        if self.view.right_widget.width() <= 50:
            self.mc.toggle_right_panel()
