import sys
import json
import uuid
import re
import os
import datetime
import csv
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QAbstractItemView, QMessageBox, QFileDialog, QApplication,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QSizePolicy,
    QScrollArea
)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, QSize

from views.components.writing_chart_view import WritingChartView
from utils.font_manager import FontManager

class MetricCard(QFrame):
    """簡約數據指標卡片。"""
    def __init__(self, title: str, value: str = "0", sub_text: str = ""):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            MetricCard {
                background-color: #252526;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        self.card_layout = QVBoxLayout(self)
        self.card_layout.setContentsMargins(10, 8, 10, 8)
        self.card_layout.setSpacing(4)

        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(FontManager.get_font(size=9))
        self.lbl_title.setStyleSheet("color: #888888;")

        self.lbl_val = QLabel(value)
        self.lbl_val.setFont(FontManager.get_font(size=14, weight=QFont.Weight.Bold))
        self.lbl_val.setStyleSheet("color: #e0e0e0;")

        self.lbl_sub = QLabel(sub_text)
        self.lbl_sub.setFont(FontManager.get_font(size=8))
        self.lbl_sub.setStyleSheet("color: #69f0ae;")

        self.card_layout.addWidget(self.lbl_title)
        self.card_layout.addWidget(self.lbl_val)
        self.card_layout.addWidget(self.lbl_sub)

    def update_values(self, value: str, sub_text: str = ""):
        self.lbl_val.setText(value)
        self.lbl_sub.setText(sub_text)

    def update_scale(self, scale: float):
        self.lbl_title.setFont(FontManager.get_font(size=max(7, int(9 * scale))))
        self.lbl_val.setFont(FontManager.get_font(size=max(10, int(14 * scale)), weight=QFont.Weight.Bold))
        self.lbl_sub.setFont(FontManager.get_font(size=max(6, int(8 * scale))))
        pad = max(6, int(10 * scale))
        rad = max(4, int(6 * scale))
        self.setStyleSheet(f"""
            MetricCard {{
                background-color: #252526;
                border: 1px solid #333333;
                border-radius: {rad}px;
                padding: {pad}px;
            }}
        """)
        if hasattr(self, "card_layout"):
            self.card_layout.setContentsMargins(int(10 * scale), int(8 * scale), int(10 * scale), int(8 * scale))
            self.card_layout.setSpacing(int(4 * scale))


class WritingLogDashboard(QWidget):
    """創作日誌與數據儀表板，支援指標卡片、圖表多視圖切換與 AI 介入度分析。"""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.scale_factor = getattr(main_window, "scale_factor", 1.0) if main_window else 1.0
        self.logs = []
        self.init_ui()
        if self.scale_factor != 1.0:
            self.update_scale(self.scale_factor)

    def minimumSizeHint(self):
        return QSize(300, 300)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.container_widget = QWidget()
        self.layout_root = QVBoxLayout(self.container_widget)
        self.layout_root.setContentsMargins(15, 15, 15, 15)
        self.layout_root.setSpacing(12)

        # 頂部列
        self.header_layout = QHBoxLayout()
        self.lbl_title = QLabel("創作日誌與寫作儀表板")
        self.lbl_title.setFont(FontManager.get_font(size=16, weight=QFont.Weight.Bold))
        self.header_layout.addWidget(self.lbl_title)
        self.header_layout.addStretch()

        self.btn_share = QPushButton("分享截圖")
        self.btn_share.setFont(FontManager.get_font(size=9))
        self.btn_share.clicked.connect(self.capture_and_share)
        self.header_layout.addWidget(self.btn_share)

        self.btn_export = QPushButton("匯出 CSV")
        self.btn_export.setFont(FontManager.get_font(size=9))
        self.btn_export.clicked.connect(self.export_csv)
        self.header_layout.addWidget(self.btn_export)

        self.btn_close = QPushButton("關閉")
        self.btn_close.setFont(FontManager.get_font(size=9))
        self.btn_close.clicked.connect(self.close_dashboard)
        self.header_layout.addWidget(self.btn_close)

        self.layout_root.addLayout(self.header_layout)

        # 指標卡片列 (4 張卡片)
        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(10)

        self.card_duration = MetricCard("總寫作時長", "0 小時", "持續創作")
        self.card_total_words = MetricCard("累積總字數", "0 字", "全書總計")
        self.card_avg_words = MetricCard("平均日寫作量", "0 字 / 天", "日均產出")
        self.card_ai_ratio = MetricCard("創作誠信與 AI 輔助", "100% 手寫原創", "無 AI 介入")

        self.cards_layout.addWidget(self.card_duration)
        self.cards_layout.addWidget(self.card_total_words)
        self.cards_layout.addWidget(self.card_avg_words)
        self.cards_layout.addWidget(self.card_ai_ratio)

        self.layout_root.addLayout(self.cards_layout)

        # 檢視模式切換列
        self.mode_layout = QHBoxLayout()
        self.mode_layout.setSpacing(8)

        self.lbl_chart_mode = QLabel("圖表視圖：")
        self.lbl_chart_mode.setFont(FontManager.get_font(size=9))
        self.mode_layout.addWidget(self.lbl_chart_mode)

        self.btn_mode_trend = QPushButton("📈 近期趨勢")
        self.btn_mode_heatmap = QPushButton("📅 打卡熱力圖")
        self.btn_mode_chapters = QPushButton("📊 各章字數")
        self.btn_mode_ai = QPushButton("🤖 AI 介入度")

        for btn in (self.btn_mode_trend, self.btn_mode_heatmap, self.btn_mode_chapters, self.btn_mode_ai):
            btn.setFont(FontManager.get_font(size=9))
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            self.mode_layout.addWidget(btn)

        self.btn_mode_trend.setChecked(True)
        self.btn_mode_trend.clicked.connect(lambda: self.switch_chart_mode("trend"))
        self.btn_mode_heatmap.clicked.connect(lambda: self.switch_chart_mode("heatmap"))
        self.btn_mode_chapters.clicked.connect(lambda: self.switch_chart_mode("chapters"))
        self.btn_mode_ai.clicked.connect(lambda: self.switch_chart_mode("ai_ratio"))

        self.mode_layout.addStretch()
        self.layout_root.addLayout(self.mode_layout)

        # 圖表繪圖元件
        self.chart_view = WritingChartView()
        self.chart_view.setMinimumHeight(180)
        self.layout_root.addWidget(self.chart_view, 1)

        # 日誌表格
        self.table = QTableWidget()
        self.table.setFont(FontManager.get_font(size=9))
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["日期", "當日總時長", "手寫字數", "AI 續寫字數", "大量異動(貼/刪)", "AI 輔助與面向"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setFixedHeight(180)
        self.layout_root.addWidget(self.table)

        self.scroll_area.setWidget(self.container_widget)
        main_layout.addWidget(self.scroll_area)

    def switch_chart_mode(self, mode: str):
        self.chart_view.set_mode(mode)

    def _extract_chapter_stats(self):
        """從 MainWindow 的章節樹中提取各章節名稱與字數。"""
        names = []
        words = []
        if not hasattr(self.main_window, 'tree_widget'):
            return names, words

        def traverse(item):
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data:
                node_type = data.get("type") or data.get("node_type")
                if node_type in ("file", "scene"):
                    content = data.get("content", "")
                    # 若當前正在編輯該節點，取得編輯器即時內容
                    if hasattr(self.main_window, "current_file_item") and self.main_window.current_file_item == item:
                        if hasattr(self.main_window, "editor") and hasattr(self.main_window.editor, "toPlainText"):
                            content = self.main_window.editor.toPlainText()
                    # 清除 HTML 與空白
                    clean = re.sub(r'<[^>]+>', '', content)
                    clean = re.sub(r'[\s\r\n\t]+', '', clean)
                    c_zh = len(re.findall(r'[\u4e00-\u9fa5]', clean))
                    c_en = len(re.findall(r'[a-zA-Z0-9]+', clean))
                    count = c_zh + c_en
                    names.append(item.text(0))
                    words.append(count)
            for i in range(item.childCount()):
                traverse(item.child(i))

        root = self.main_window.tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
            traverse(root.child(i))

        return names, words

    def refresh_data(self, logs=None):
        if logs is not None:
            self.logs = logs
        else:
            self.logs = getattr(self.main_window, 'writing_logs', self.logs)

        # 讀取主題顏色
        theme = getattr(self.main_window, 'current_theme', 'default')
        if theme == "default":
            self.chart_view.set_theme_colors(QColor("#69f0ae"), QColor("#00e676"))
        elif theme == "green":
            self.chart_view.set_theme_colors(QColor("#43a047"), QColor("#1f4c32"))
        elif theme == "celadon":
            self.chart_view.set_theme_colors(QColor("#00a8cc"), QColor("#1d4e6e"))
        elif theme == "sepia":
            self.chart_view.set_theme_colors(QColor("#d7ba7d"), QColor("#8c7047"))
        elif theme == "polar":
            self.chart_view.set_theme_colors(QColor("#4fc3f7"), QColor("#0288d1"))
        elif theme == "forest":
            self.chart_view.set_theme_colors(QColor("#81c784"), QColor("#388e3c"))

        # 計算指標卡片總數值
        total_duration = sum(l.get("duration", 0) for l in self.logs)
        total_words = sum(l.get("word_count", 0) for l in self.logs)
        total_ai_chars = sum(l.get("ai_continuation_chars", 0) for l in self.logs)
        total_ai_chats = sum(l.get("ai_chat_count", 0) for l in self.logs)
        total_manual_words = max(0, total_words - total_ai_chars)

        # 彙整 AI 細部面向
        total_structuring = 0
        total_editorial = 0
        total_brainstorming = 0
        for l in self.logs:
            details = l.get("ai_details", {})
            if isinstance(details, dict):
                total_structuring += details.get("character", 0) + details.get("world", 0) + details.get("timeline", 0)
                total_editorial += details.get("proofread", 0) + details.get("impression", 0)
                total_brainstorming += details.get("chat", 0)

        all_interactions = total_ai_chats if total_ai_chats > 0 else (total_structuring + total_editorial + total_brainstorming)
        if total_structuring == 0 and total_editorial == 0 and total_brainstorming == 0 and total_ai_chats > 0:
            total_brainstorming = total_ai_chats

        active_days = len([l for l in self.logs if l.get("word_count", 0) > 0 or l.get("duration", 0) > 0])
        avg_words = int(total_words / max(1, active_days))

        total_hours = total_duration // 3600
        total_mins = (total_duration % 3600) // 60
        self.card_duration.update_values(f"{total_hours} 小時 {total_mins} 分", f"活躍寫作 {active_days} 天")
        self.card_total_words.update_values(f"{total_words:,} 字", f"含手寫 {total_manual_words:,} 字")
        self.card_avg_words.update_values(f"{avg_words:,} 字 / 天", f"連續紀錄中")

        handcrafted_pct = 100 if total_words == 0 else int((total_manual_words / max(1, total_words)) * 100)
        if total_ai_chars == 0:
            card_main_val = f"{handcrafted_pct}% 純手創"
        else:
            card_main_val = f"{handcrafted_pct}% 手創 (代筆 {total_ai_chars:,}字)"

        if all_interactions == 0 and total_ai_chars == 0:
            card_sub_val = "100% 獨立原創 | 零 AI 介入"
        else:
            if total_ai_chars > 0:
                card_sub_val = f"含正文擴寫 | 輔助 {all_interactions} 次"
            elif total_editorial >= total_structuring and total_editorial > 0:
                card_sub_val = f"定位：文字校審評語 ({all_interactions} 次)"
            elif total_structuring > 0:
                card_sub_val = f"定位：設定架構整理 ({all_interactions} 次)"
            elif total_brainstorming > 0:
                card_sub_val = f"定位：靈感對話助手 ({all_interactions} 次)"
            else:
                card_sub_val = f"輔助互動 {all_interactions} 次 | 0 字代筆"

        total_paste_large = sum(l.get("paste_large_count", 0) for l in self.logs)
        total_delete_large = sum(l.get("delete_large_count", 0) for l in self.logs)

        self.card_ai_ratio.update_values(card_main_val, card_sub_val)

        # 填充表格
        self.table.clearContents()
        self.table.setRowCount(0)

        sorted_logs_desc = sorted(self.logs, key=lambda x: x.get("date", ""), reverse=True)
        for log in sorted_logs_desc:
            date_str = log.get("date", "")
            duration = log.get("duration", 0)
            word_count = log.get("word_count", 0)
            ai_chars = log.get("ai_continuation_chars", 0)
            ai_chats = log.get("ai_chat_count", 0)

            hours = duration // 3600
            minutes = (duration % 3600) // 60
            seconds = duration % 60

            if hours > 0:
                duration_str = f"{hours} 小時 {minutes} 分"
            elif minutes > 0:
                duration_str = f"{minutes} 分 {seconds} 秒"
            else:
                duration_str = f"{seconds} 秒"

            manual_words = max(0, word_count - ai_chars)

            details = log.get("ai_details", {})
            structuring = 0
            editorial = 0
            chat = 0
            continuation = 0
            if isinstance(details, dict):
                structuring = details.get("character", 0) + details.get("world", 0) + details.get("timeline", 0)
                editorial = details.get("proofread", 0) + details.get("impression", 0)
                chat = details.get("chat", 0)
                continuation = details.get("continuation", 0)

            day_interactions = ai_chats if ai_chats > 0 else (structuring + editorial + chat + continuation)
            if structuring == 0 and editorial == 0 and chat == 0 and ai_chats > 0:
                chat = ai_chats

            tags = []
            if editorial > 0:
                tags.append(f"[🔍校審 {editorial}]")
            if structuring > 0:
                tags.append(f"[🧩整理 {structuring}]")
            if chat > 0:
                tags.append(f"[💬靈感 {chat}]")
            if continuation > 0:
                tags.append(f"[✍️擴寫 {continuation}]")

            tag_str = " ".join(tags)
            if day_interactions == 0 and continuation == 0:
                chat_display = "0 次"
            elif tag_str:
                chat_display = f"{day_interactions} 次  {tag_str}"
            else:
                chat_display = f"{day_interactions} 次"

            paste_cnt = log.get("paste_large_count", 0)
            delete_cnt = log.get("delete_large_count", 0)
            mod_tags = []
            if paste_cnt > 0:
                mod_tags.append(f"[📋貼上 {paste_cnt}]")
            if delete_cnt > 0:
                mod_tags.append(f"[✂️刪除 {delete_cnt}]")
            mod_display = " ".join(mod_tags) if mod_tags else "無"

            date_item = QTableWidgetItem(date_str)
            duration_item = QTableWidgetItem(duration_str)
            manual_item = QTableWidgetItem(f"{manual_words:,}")
            ai_item = QTableWidgetItem(f"{ai_chars:,}")
            mod_item = QTableWidgetItem(mod_display)
            chat_item = QTableWidgetItem(chat_display)

            mod_item.setToolTip(
                f"【{date_str} 異常異動明細】\n"
                f"• 短時間大量貼上(>300字)：{paste_cnt} 次\n"
                f"• 短時間大量刪除(>300字)：{delete_cnt} 次\n"
                "────────────────────────\n"
                "備註：超過300字之非正常連續鍵入變更"
            )

            tooltip_lines = [
                f"【{date_str} AI 輔助誠信明細】",
                f"• 親筆手寫字數：{manual_words:,} 字",
                f"• AI 續寫字數：{ai_chars:,} 字" + (f" ({continuation} 次)" if continuation else ""),
                f"• 責任編輯審校：{editorial} 次 (校稿、文學評語)",
                f"• 設定架構整理：{structuring} 次 (角色、世界觀、時間線)",
                f"• 靈感對話助手：{chat} 次",
                "────────────────────────",
                "誠信備註：除擴寫外，其餘功能皆為結構/校對輔助，不代筆正文。"
            ]
            chat_item.setToolTip("\n".join(tooltip_lines))

            for item in (date_item, duration_item, manual_item, ai_item, mod_item, chat_item):
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            self.table.setItem(row_idx, 0, date_item)
            self.table.setItem(row_idx, 1, duration_item)
            self.table.setItem(row_idx, 2, manual_item)
            self.table.setItem(row_idx, 3, ai_item)
            self.table.setItem(row_idx, 4, mod_item)
            self.table.setItem(row_idx, 5, chat_item)

        # 傳遞數據至 ChartView（含全量歷史打卡查找表與大量異動次數）
        sorted_logs_asc = sorted(self.logs, key=lambda x: x.get("date", ""))
        recent_logs = sorted_logs_asc[-14:] if len(sorted_logs_asc) > 14 else sorted_logs_asc
        recent_dates = [x.get("date", "") for x in recent_logs]
        recent_values = [max(0, x.get("word_count", 0)) for x in recent_logs]
        recent_ai_chars = [max(0, x.get("ai_continuation_chars", 0)) for x in recent_logs]
        recent_ai_chats = [max(0, x.get("ai_chat_count", 0)) for x in recent_logs]
        recent_ai_details = [x.get("ai_details", {}) for x in recent_logs]

        full_date_map = {x.get("date", ""): max(0, x.get("word_count", 0)) for x in self.logs if x.get("date")}

        self.chart_view.set_data(
            recent_dates, recent_values, recent_ai_chars, recent_ai_chats, recent_ai_details,
            full_date_map=full_date_map,
            total_paste_large=total_paste_large,
            total_delete_large=total_delete_large
        )

        # 傳遞章節統計數據
        ch_names, ch_words = self._extract_chapter_stats()
        self.chart_view.set_chapter_stats(ch_names, ch_words)

    def capture_and_share(self):
        target_widget = getattr(self, "container_widget", self)
        pixmap = target_widget.grab()
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(pixmap)
        QMessageBox.information(self, "成功", "寫作儀表板截圖已成功複製至系統剪貼簿！")

    def export_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "匯出創作日誌", "", "CSV Files (*.csv)")
        if not file_path:
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["日期", "當日總寫作時長(秒)", "當日總時長(格式化)", "今日總字數", "手寫字數", "AI續寫字數", "大量貼上(>300字)次數", "大量刪除(>300字)次數", "AI總輔助次數", "AI設定整理次數", "AI文字審校次數", "AI靈感對話次數"])

                sorted_logs = sorted(self.logs, key=lambda x: x.get("date", ""))

                for log in sorted_logs:
                    date_str = log.get("date", "")
                    duration = log.get("duration", 0)
                    word_count = log.get("word_count", 0)
                    ai_chars = log.get("ai_continuation_chars", 0)
                    ai_chats = log.get("ai_chat_count", 0)
                    paste_cnt = log.get("paste_large_count", 0)
                    delete_cnt = log.get("delete_large_count", 0)

                    details = log.get("ai_details", {})
                    structuring = 0
                    editorial = 0
                    chat = 0
                    if isinstance(details, dict):
                        structuring = details.get("character", 0) + details.get("world", 0) + details.get("timeline", 0)
                        editorial = details.get("proofread", 0) + details.get("impression", 0)
                        chat = details.get("chat", 0)
                    total_act = ai_chats if ai_chats > 0 else (structuring + editorial + chat)
                    if structuring == 0 and editorial == 0 and chat == 0 and ai_chats > 0:
                        chat = ai_chats

                    hours = duration // 3600
                    minutes = (duration % 3600) // 60
                    seconds = duration % 60

                    if hours > 0:
                        duration_str = f"{hours} 小時 {minutes} 分鐘"
                    elif minutes > 0:
                        duration_str = f"{minutes} 分鐘 {seconds} 秒"
                    else:
                        duration_str = f"{seconds} 秒"

                    manual_words = max(0, word_count - ai_chars)

                    writer.writerow([
                        date_str,
                        duration,
                        duration_str,
                        word_count,
                        manual_words,
                        ai_chars,
                        paste_cnt,
                        delete_cnt,
                        total_act,
                        structuring,
                        editorial,
                        chat
                    ])
            QMessageBox.information(self, "成功", "創作日誌與 AI 數據已成功匯出至 CSV 檔案！")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"匯出時發生錯誤：{e}")

    def close_dashboard(self):
        self.main_window.center_stack.setCurrentIndex(0)

    def update_scale(self, scale: float):
        """依據縮放比例更新儀表板字型、卡片大小與圖表/表格尺寸。"""
        self.scale_factor = scale
        fam = getattr(self.main_window, "global_font_family", None) or FontManager.get_default_font_family()

        if hasattr(self, "layout_root"):
            self.layout_root.setContentsMargins(int(15 * scale), int(15 * scale), int(15 * scale), int(15 * scale))
            self.layout_root.setSpacing(int(12 * scale))
        if hasattr(self, "cards_layout"):
            self.cards_layout.setSpacing(int(10 * scale))
        if hasattr(self, "mode_layout"):
            self.mode_layout.setSpacing(int(8 * scale))

        self.lbl_title.setFont(FontManager.get_font(family=fam, size=max(12, int(16 * scale)), weight=QFont.Weight.Bold))
        for btn in (self.btn_share, self.btn_export, self.btn_close):
            btn.setFont(FontManager.get_font(family=fam, size=max(7, int(9 * scale))))
            btn.setFixedHeight(max(24, int(30 * scale)))

        self.card_duration.update_scale(scale)
        self.card_total_words.update_scale(scale)
        self.card_avg_words.update_scale(scale)
        self.card_ai_ratio.update_scale(scale)

        if hasattr(self, "lbl_chart_mode"):
            self.lbl_chart_mode.setFont(FontManager.get_font(family=fam, size=max(7, int(9 * scale))))
        for btn in (self.btn_mode_trend, self.btn_mode_heatmap, self.btn_mode_chapters, self.btn_mode_ai):
            btn.setFont(FontManager.get_font(family=fam, size=max(7, int(9 * scale))))
            btn.setFixedHeight(max(24, int(28 * scale)))

        if hasattr(self, "chart_view"):
            self.chart_view.set_scale(scale)
            self.chart_view.setMinimumHeight(max(180, int(200 * scale)))

        if hasattr(self, "table"):
            self.table.setFont(FontManager.get_font(family=fam, size=max(7, int(9 * scale))))
            self.table.horizontalHeader().setFont(FontManager.get_font(family=fam, size=max(7, int(9 * scale)), weight=QFont.Weight.Bold))
            self.table.horizontalHeader().setFixedHeight(max(24, int(30 * scale)))
            self.table.verticalHeader().setDefaultSectionSize(max(22, int(28 * scale)))
            self.table.setFixedHeight(max(160, int(190 * scale)))

