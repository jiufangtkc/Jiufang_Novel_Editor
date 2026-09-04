import re
import datetime
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QDialog
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextDocument
from models.models import WritingLogEntry
from views.dialogs.word_count_settings_dialog import WordCountSettingsDialog
from services.app_settings_service import AppSettingsService

class StatsController:
    """負責字數統計、排除規則分析、狀態列更新、寫作計時器與創作日誌。"""

    def __init__(self, main_controller):
        self.mc = main_controller
        self._paste_window_words: int = 0
        self._paste_window_time = None
        self._delete_window_chars: int = 0
        self._delete_window_time = None

    @property
    def view(self):
        return self.mc.view

    def count_words(self, text: str) -> int:
        if not text:
            return 0
        return self.analyze_exclusions(text)["valid"]

    def analyze_exclusions(self, text: str) -> dict:
        if not text:
            return {
                "valid": 0, "cjk": 0, "half_alnum_sym": 0,
                "half_spaces": 0, "full_spaces": 0,
                "spaces": 0, "alpha": 0, "sym": 0
            }

        count_half = False
        count_full_space = False
        if hasattr(self.mc, "app_settings") and isinstance(self.mc.app_settings, dict):
            count_half = bool(self.mc.app_settings.get("stat_count_half_alnum_and_sym", False))
            count_full_space = bool(self.mc.app_settings.get("stat_count_full_space", False))

        # 全形中文字（含全形標點符號，排除半形英數符號空白及全形空格）
        cjk_text = re.sub(r'[a-zA-Z0-9\s\u3000!"#$%&\'()*+,\-./:;<=>?@\[\\\]^_`{|}~]', '', text)
        cjk_count = len(cjk_text)

        # 半形英數字與半形符號
        alphanumerics = len(re.findall(r'[a-zA-Z0-9]', text))
        half_symbols = len(re.findall(r'[!"#$%&\'()*+,\-./:;<=>?@\[\\\]^_`{|}~]', text))
        half_alnum_sym = alphanumerics + half_symbols

        # 空格分類
        half_spaces = len(re.findall(r'[ \t]', text))
        full_spaces = len(re.findall(r'[\u3000]', text))
        total_spaces = len(re.findall(r'[\s\u3000]', text))

        # 計算有效統計字數
        valid_words = cjk_count
        if count_half:
            valid_words += half_alnum_sym + half_spaces
        if count_full_space:
            valid_words += full_spaces

        return {
            "valid": valid_words,
            "cjk": cjk_count,
            "half_alnum_sym": half_alnum_sym,
            "half_spaces": half_spaces,
            "full_spaces": full_spaces,
            "spaces": total_spaces,
            "alpha": alphanumerics,
            "sym": half_symbols
        }

    def analyze_exclusions_from_markdown(self, markdown_text: str) -> dict:
        return self.analyze_exclusions(markdown_text)

    def recalculate_all_word_stats(self):
        """當字數統計規則改變時，重新計算所有章節節點與當前編輯頁面的字數統計。"""
        self.mc.save_current_editor_content()

        def process_item(item):
            if not self.mc.tree.is_item_valid(item):
                return
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") in ("file", "scene"):
                item_id = data.get("id")
                content = data.get("content", "")
                if item_id:
                    self.mc.file_word_stats[item_id] = self.analyze_exclusions(content)
            for i in range(item.childCount()):
                process_item(item.child(i))

        for i in range(self.view.tree_widget.topLevelItemCount()):
            process_item(self.view.tree_widget.topLevelItem(i))

        if self.mc.current_file_item and self.mc.tree.is_item_valid(self.mc.current_file_item):
            curr_id = self.mc.tree.get_item_id(self.mc.current_file_item)
            if curr_id:
                self.mc.file_word_stats[curr_id] = self.analyze_exclusions(self.view.editor.toPlainText())

        self.mc.last_known_word_count = sum(x.get("valid", 0) for x in self.mc.file_word_stats.values())

    def update_status_bar(self):
        if not self.mc.tree.is_item_valid(self.mc.current_file_item):
            self.mc.current_file_item = None

        page_cjk = 0
        page_half = 0
        page_half_sp = 0
        page_full_sp = 0
        page_valid = 0

        if self.mc.current_file_item:
            stats = self.analyze_exclusions(self.view.editor.toPlainText())
            page_valid = stats["valid"]
            page_cjk = stats.get("cjk", 0)
            page_half = stats.get("half_alnum_sym", 0)
            page_half_sp = stats.get("half_spaces", 0)
            page_full_sp = stats.get("full_spaces", 0)

        total_valid = sum(x.get("valid", 0) for x in self.mc.file_word_stats.values())
        total_cjk = sum(x.get("cjk", 0) for x in self.mc.file_word_stats.values())
        total_half = sum(x.get("half_alnum_sym", 0) for x in self.mc.file_word_stats.values())
        total_half_sp = sum(x.get("half_spaces", 0) for x in self.mc.file_word_stats.values())
        total_full_sp = sum(x.get("full_spaces", 0) for x in self.mc.file_word_stats.values())

        self.view.lbl_word_count.setText(f"本頁: {page_valid} 字 | 全文: {total_valid} 字")

        count_half = bool(self.mc.app_settings.get("stat_count_half_alnum_and_sym", False)) if hasattr(self.mc, "app_settings") else False
        count_full_space = bool(self.mc.app_settings.get("stat_count_full_space", False)) if hasattr(self.mc, "app_settings") else False

        status_half_text = "計入統計" if count_half else "已排除"
        status_full_text = "計入統計" if count_full_space else "已排除"

        tooltip_text = (
            f"<b>字數詳細統計</b><br/>"
            f"──────────────────<br/>"
            f"<b>【本頁輸入統計】</b><br/>"
            f"• 全形中文（含全形標點）：{page_cjk} 字<br/>"
            f"• 半形英數（含半形符號）：{page_half} 字<br/>"
            f"• 半形空格：{page_half_sp} 個<br/>"
            f"• 全形空格：{page_full_sp} 個<br/>"
            f"<br/>"
            f"<b>【全文輸入統計】</b><br/>"
            f"• 全形中文（含全形標點）：{total_cjk} 字<br/>"
            f"• 半形英數（含半形符號）：{total_half} 字<br/>"
            f"• 半形空格：{total_half_sp} 個<br/>"
            f"• 全形空格：{total_full_sp} 個<br/>"
            f"<br/>"
            f"<b>【統計規則狀態】</b><br/>"
            f"• 半形英數/符號/空格：{status_half_text}<br/>"
            f"• 全形空格：{status_full_text}<br/>"
            f"──────────────────<br/>"
            f"<b>當前生效總字數：</b>本頁 {page_valid} 字 | 全文 {total_valid} 字"
        )
        self.view.lbl_word_count.setToolTip(tooltip_text)

        # 1. 今日寫作進度條更新
        self.view.progress_bar.setMaximum(self.mc.today_target)
        self.view.progress_bar.setValue(min(self.mc.today_written_count, self.mc.today_target))
        percent = int((self.mc.today_written_count / self.mc.today_target) * 100) if self.mc.today_target > 0 else 0
        self.view.lbl_progress.setText(f"今日進度: {self.mc.today_written_count} / {self.mc.today_target} 字 ({percent}%)")

        # 2. 寫作專案總進度條更新
        if hasattr(self.view, "project_progress_bar") and hasattr(self.view, "lbl_project_progress"):
            proj_target = getattr(self.mc.project_info, "target_word_count", 100000)
            if proj_target <= 0:
                proj_target = 100000
            self.view.project_progress_bar.setMaximum(proj_target)
            self.view.project_progress_bar.setValue(min(total_valid, proj_target))
            proj_percent = int((total_valid / proj_target) * 100) if proj_target > 0 else 0
            self.view.lbl_project_progress.setText(f"專案總進度: {total_valid} / {proj_target} 字 ({proj_percent}%)")

    def set_daily_target(self):
        target, ok = QInputDialog.getInt(self.view, "設定今日目標", "請輸入今日寫作目標字數：", value=self.mc.today_target, min=10)
        if ok and target > 0:
            self.mc.today_target = target
            self.mc.project_info.daily_target_word_count = target
            self.view.progress_bar.setMaximum(self.mc.today_target)
            self.update_status_bar()
            self.mc.save_temp_doc()

    def set_project_target(self):
        curr_target = getattr(self.mc.project_info, "target_word_count", 100000)
        target, ok = QInputDialog.getInt(
            self.view, "設定專案目標", "請輸入寫作專案總目標字數：",
            value=curr_target, min=100, max=10000000, step=10000
        )
        if ok and target > 0:
            self.mc.project_info.target_word_count = target
            self.update_status_bar()
            self.mc.save_temp_doc()

    def open_word_count_settings_dialog(self):
        count_half = bool(self.mc.app_settings.get("stat_count_half_alnum_and_sym", False)) if hasattr(self.mc, "app_settings") else False
        count_full = bool(self.mc.app_settings.get("stat_count_full_space", False)) if hasattr(self.mc, "app_settings") else False
        dialog = WordCountSettingsDialog(
            self.view,
            count_half_alnum_and_sym=count_half,
            count_full_space=count_full
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_half, new_full = dialog.get_settings()
            self.mc.app_settings["stat_count_half_alnum_and_sym"] = new_half
            self.mc.app_settings["stat_count_full_space"] = new_full
            AppSettingsService.save_settings(self.mc.app_settings, self.mc.app_dir)
            self.recalculate_all_word_stats()
            self.update_status_bar()

    def clear_daily_progress(self):
        reply = QMessageBox.question(
            self.view, "確認清除", "您確定要清除今日的寫作進度嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.mc.today_written_count = 0
            today_str = datetime.datetime.now().strftime("%Y-%m-%d")
            for log in self.mc.writing_logs:
                if log.date == today_str:
                    log.word_count = 0
                    break
            self.update_status_bar()
            self.mc.save_temp_doc()

    def on_document_contents_change(self, position, charsRemoved, charsAdded):
        if self.view.editor.signalsBlocked():
            return
        if not self.mc.tree.is_item_valid(self.mc.current_file_item):
            self.mc.current_file_item = None

        now = datetime.datetime.now()

        # 監控大量刪除文字行為（單次或2秒內累計超過300字元）
        if charsRemoved > 0 and self.mc.current_file_item is not None:
            if charsRemoved >= 300:
                self.record_text_modification(delete_large=True)
                self._delete_window_chars = 0
                self._delete_window_time = None
            else:
                if self._delete_window_time and (now - self._delete_window_time).total_seconds() <= 2.0:
                    self._delete_window_chars += charsRemoved
                else:
                    self._delete_window_chars = charsRemoved
                self._delete_window_time = now

                if self._delete_window_chars >= 300:
                    self.record_text_modification(delete_large=True)
                    self._delete_window_chars = 0
                    self._delete_window_time = None

        current_page_words = 0
        if self.mc.current_file_item:
            current_page_words = self.count_words(self.view.editor.toPlainText())

        current_total = 0
        current_item_id = self.mc.tree.get_item_id(self.mc.current_file_item)
        for item_id, stats in self.mc.file_word_stats.items():
            if item_id != current_item_id:
                current_total += stats.get("valid", 0)
        current_total += current_page_words

        delta = current_total - self.mc.last_known_word_count

        if self.mc.active_session is None:
            self.mc.active_session = {
                "start_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "last_action_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "words_added": max(0, delta)
            }
        else:
            self.mc.active_session["last_action_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
            if delta > 0:
                self.mc.active_session["words_added"] = self.mc.active_session.get("words_added", 0) + delta

        self.mc.last_known_word_count = current_total

    def check_writing_inactivity(self):
        if self.mc.active_session:
            now = datetime.datetime.now()
            last_action = datetime.datetime.strptime(self.mc.active_session["last_action_time"], "%Y-%m-%d %H:%M:%S")
            inactive_secs = (now - last_action).total_seconds()
            if inactive_secs > 60:
                self.flush_active_writing_session()

    def flush_active_writing_session(self):
        if self.mc.active_session:
            now = datetime.datetime.now()
            start_time_str = self.mc.active_session["start_time"]
            last_action_str = self.mc.active_session["last_action_time"]

            start_dt = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
            last_action_dt = datetime.datetime.strptime(last_action_str, "%Y-%m-%d %H:%M:%S")

            duration_secs = (last_action_dt - start_dt).total_seconds()
            words_diff = max(0, self.mc.active_session.get("words_added", 0))

            if duration_secs > 0:
                date_str = start_time_str.split(" ")[0]
                today_date_str = now.strftime("%Y-%m-%d")
                found = False
                for log in self.mc.writing_logs:
                    if log.date == date_str:
                        log.duration += int(duration_secs)
                        target_wc = log.word_count + words_diff
                        if date_str == today_date_str:
                            target_wc = max(target_wc, getattr(self.mc, "today_written_count", 0))
                        log.word_count = max(0, target_wc)
                        found = True
                        break
                if not found:
                    initial_wc = words_diff
                    if date_str == today_date_str:
                        initial_wc = max(initial_wc, getattr(self.mc, "today_written_count", 0))
                    self.mc.writing_logs.append(WritingLogEntry(
                        date=date_str,
                        duration=int(duration_secs),
                        word_count=max(0, initial_wc)
                    ))

                self.view.writing_log_dashboard.refresh_data(self.mc.get_writing_logs_as_dict())

            self.mc.active_session = None

    def record_ai_activity(self, continuation_count: int = 0, continuation_chars: int = 0, chat_count: int = 0, feature_key: str = ""):
        """記錄並累計當日的 AI 介入度數據（續寫次數/字數、對話次數，以及細部功能面向）。"""
        now_date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        found = False
        for log in self.mc.writing_logs:
            if log.date == now_date_str:
                log.ai_continuation_count = getattr(log, "ai_continuation_count", 0) + continuation_count
                log.ai_continuation_chars = getattr(log, "ai_continuation_chars", 0) + continuation_chars
                log.ai_chat_count = getattr(log, "ai_chat_count", 0) + chat_count
                if not hasattr(log, "ai_details") or not isinstance(log.ai_details, dict):
                    log.ai_details = {}
                if feature_key:
                    log.ai_details[feature_key] = log.ai_details.get(feature_key, 0) + 1
                found = True
                break
        if not found:
            details = {}
            if feature_key:
                details[feature_key] = 1
            self.mc.writing_logs.append(WritingLogEntry(
                date=now_date_str,
                duration=0,
                word_count=0,
                ai_continuation_count=continuation_count,
                ai_continuation_chars=continuation_chars,
                ai_chat_count=chat_count,
                ai_details=details
            ))
        self.mc.save_temp_doc()
        if getattr(self.view, 'writing_log_dashboard', None) is not None:
            self.view.writing_log_dashboard.refresh_data(self.mc.get_writing_logs_as_dict())

    def on_text_pasted(self, pasted_text: str):
        """偵測短時間或單次超過 300 字以上的貼上行為次數。"""
        if not pasted_text or self.view.editor.signalsBlocked():
            return
        if not self.mc.tree.is_item_valid(self.mc.current_file_item):
            return

        now = datetime.datetime.now()
        words = self.count_words(pasted_text)
        if words == 0:
            words = len(pasted_text.strip())

        if words >= 300:
            self.record_text_modification(paste_large=True)
            self._paste_window_words = 0
            self._paste_window_time = None
        else:
            if self._paste_window_time and (now - self._paste_window_time).total_seconds() <= 2.0:
                self._paste_window_words += words
            else:
                self._paste_window_words = words
            self._paste_window_time = now

            if self._paste_window_words >= 300:
                self.record_text_modification(paste_large=True)
                self._paste_window_words = 0
                self._paste_window_time = None

    def record_text_modification(self, paste_large: bool = False, delete_large: bool = False):
        """記錄並累計當日的大量貼上文字與大量刪除文字次數。"""
        if not paste_large and not delete_large:
            return
        now_date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        found = False
        for log in self.mc.writing_logs:
            if log.date == now_date_str:
                if paste_large:
                    log.paste_large_count = getattr(log, "paste_large_count", 0) + 1
                if delete_large:
                    log.delete_large_count = getattr(log, "delete_large_count", 0) + 1
                found = True
                break
        if not found:
            self.mc.writing_logs.append(WritingLogEntry(
                date=now_date_str,
                duration=0,
                word_count=0,
                paste_large_count=1 if paste_large else 0,
                delete_large_count=1 if delete_large else 0
            ))
        self.mc.save_temp_doc()
        if getattr(self.view, 'writing_log_dashboard', None) is not None:
            self.view.writing_log_dashboard.refresh_data(self.mc.get_writing_logs_as_dict())

    def show_writing_log_dashboard(self):
        self.mc.save_current_editor_content()
        self.flush_active_writing_session()
        scale = getattr(self.view, "scale_factor", 1.0)
        if hasattr(self.view, "writing_log_dashboard") and hasattr(self.view.writing_log_dashboard, "update_scale"):
            self.view.writing_log_dashboard.update_scale(scale)
        self.view.writing_log_dashboard.refresh_data(self.mc.get_writing_logs_as_dict())
        self.view.center_stack.setCurrentIndex(2)

