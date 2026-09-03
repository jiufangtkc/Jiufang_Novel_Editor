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
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QSizePolicy
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(FontManager.get_font(size=9))
        self.lbl_title.setStyleSheet("color: #888888;")

        self.lbl_val = QLabel(value)
        self.lbl_val.setFont(FontManager.get_font(size=14, weight=QFont.Weight.Bold))
        self.lbl_val.setStyleSheet("color: #e0e0e0;")

        self.lbl_sub = QLabel(sub_text)
        self.lbl_sub.setFont(FontManager.get_font(size=8))
        self.lbl_sub.setStyleSheet("color: #69f0ae;")

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_val)
        layout.addWidget(self.lbl_sub)

    def update_values(self, value: str, sub_text: str = ""):
        self.lbl_val.setText(value)
        self.lbl_sub.setText(sub_text)

    def update_scale(self, scale: float):
        self.lbl_title.setFont(FontManager.get_font(size=int(9 * scale)))
        self.lbl_val.setFont(FontManager.get_font(size=int(14 * scale), weight=QFont.Weight.Bold))
        self.lbl_sub.setFont(FontManager.get_font(size=int(8 * scale)))
        pad = int(10 * scale)
        rad = int(6 * scale)
        self.setStyleSheet(f"""
            MetricCard {{
                background-color: #252526;
                border: 1px solid #333333;
                border-radius: {rad}px;
                padding: {pad}px;
            }}
        """)


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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # 頂部列
        header_layout = QHBoxLayout()
        self.lbl_title = QLabel("創作日誌與寫作儀表板")
        self.lbl_title.setFont(FontManager.get_font(size=16, weight=QFont.Weight.Bold))
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()

        self.btn_share = QPushButton("分享截圖")
        self.btn_share.setFont(FontManager.get_font(size=9))
        self.btn_share.clicked.connect(self.capture_and_share)
        header_layout.addWidget(self.btn_share)

        self.btn_export = QPushButton("匯出 CSV")
        self.btn_export.setFont(FontManager.get_font(size=9))
        self.btn_export.clicked.connect(self.export_csv)
        header_layout.addWidget(self.btn_export)

        self.btn_close = QPushButton("關閉")
        self.btn_close.setFont(FontManager.get_font(size=9))
        self.btn_close.clicked.connect(self.close_dashboard)
        header_layout.addWidget(self.btn_close)

        layout.addLayout(header_layout)

        # 指標卡片列 (4 張卡片)
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)

        self.card_duration = MetricCard("總寫作時長", "0 小時", "持續創作")
        self.card_total_words = MetricCard("累積總字數", "0 字", "全書總計")
        self.card_avg_words = MetricCard("平均日寫作量", "0 字 / 天", "日均產出")
        self.card_ai_ratio = MetricCard("AI 輔助介入度", "0 字", "佔比 0%")

        cards_layout.addWidget(self.card_duration)
        cards_layout.addWidget(self.card_total_words)
        cards_layout.addWidget(self.card_avg_words)
        cards_layout.addWidget(self.card_ai_ratio)

        layout.addLayout(cards_layout)

        # 檢視模式切換列
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(8)

        self.lbl_chart_mode = QLabel("圖表視圖：")
        self.lbl_chart_mode.setFont(FontManager.get_font(size=9))
        mode_layout.addWidget(self.lbl_chart_mode)

        self.btn_mode_trend = QPushButton("📈 近期趨勢")
        self.btn_mode_heatmap = QPushButton("📅 打卡熱力圖")
        self.btn_mode_chapters = QPushButton("📊 各章字數")
        self.btn_mode_ai = QPushButton("🤖 AI 介入度")

        for btn in (self.btn_mode_trend, self.btn_mode_heatmap, self.btn_mode_chapters, self.btn_mode_ai):
            btn.setFont(FontManager.get_font(size=9))
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            mode_layout.addWidget(btn)

        self.btn_mode_trend.setChecked(True)
        self.btn_mode_trend.clicked.connect(lambda: self.switch_chart_mode("trend"))
        self.btn_mode_heatmap.clicked.connect(lambda: self.switch_chart_mode("heatmap"))
        self.btn_mode_chapters.clicked.connect(lambda: self.switch_chart_mode("chapters"))
        self.btn_mode_ai.clicked.connect(lambda: self.switch_chart_mode("ai_ratio"))

        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # 圖表繪圖元件
        self.chart_view = WritingChartView()
        self.chart_view.setMinimumHeight(180)
        layout.addWidget(self.chart_view, 1)

        # 日誌表格
        self.table = QTableWidget()
        self.table.setFont(FontManager.get_font(size=9))
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["日期", "當日總時長", "手寫字數", "AI 續寫字數", "AI 互動次數"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setFixedHeight(180)
        layout.addWidget(self.table)

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
            if data and data.get("node_type") in ("file", "scene"):
                content = data.get("content", "")
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

        active_days = len([l for l in self.logs if l.get("word_count", 0) > 0 or l.get("duration", 0) > 0])
        avg_words = int(total_words / max(1, active_days))

        total_hours = total_duration // 3600
        total_mins = (total_duration % 3600) // 60
        self.card_duration.update_values(f"{total_hours} 小時 {total_mins} 分", f"活躍寫作 {active_days} 天")
        self.card_total_words.update_values(f"{total_words:,} 字", f"含手寫 {max(0, total_words - total_ai_chars):,} 字")
        self.card_avg_words.update_values(f"{avg_words:,} 字 / 天", f"連續紀錄中")

        ai_pct = int((total_ai_chars / max(1, total_words)) * 100)
        self.card_ai_ratio.update_values(f"{total_ai_chars:,} 字", f"佔比 {ai_pct}% | 互動 {total_ai_chats} 次")

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

            date_item = QTableWidgetItem(date_str)
            duration_item = QTableWidgetItem(duration_str)
            manual_item = QTableWidgetItem(f"{manual_words:,}")
            ai_item = QTableWidgetItem(f"{ai_chars:,}")
            chat_item = QTableWidgetItem(str(ai_chats))

            for item in (date_item, duration_item, manual_item, ai_item, chat_item):
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            self.table.setItem(row_idx, 0, date_item)
            self.table.setItem(row_idx, 1, duration_item)
            self.table.setItem(row_idx, 2, manual_item)
            self.table.setItem(row_idx, 3, ai_item)
            self.table.setItem(row_idx, 4, chat_item)

        # 傳遞數據至 ChartView
        sorted_logs_asc = sorted(self.logs, key=lambda x: x.get("date", ""))
        recent_logs = sorted_logs_asc[-14:] if len(sorted_logs_asc) > 14 else sorted_logs_asc
        recent_dates = [x.get("date", "") for x in recent_logs]
        recent_values = [max(0, x.get("word_count", 0)) for x in recent_logs]
        recent_ai_chars = [max(0, x.get("ai_continuation_chars", 0)) for x in recent_logs]
        recent_ai_chats = [max(0, x.get("ai_chat_count", 0)) for x in recent_logs]

        self.chart_view.set_data(recent_dates, recent_values, recent_ai_chars, recent_ai_chats)

        # 傳遞章節統計數據
        ch_names, ch_words = self._extract_chapter_stats()
        self.chart_view.set_chapter_stats(ch_names, ch_words)

    def capture_and_share(self):
        pixmap = self.grab()
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
                writer.writerow(["日期", "當日總寫作時長(秒)", "當日總時長(格式化)", "今日總字數", "手寫字數", "AI續寫字數", "AI互動次數"])

                sorted_logs = sorted(self.logs, key=lambda x: x.get("date", ""))

                for log in sorted_logs:
                    date_str = log.get("date", "")
                    duration = log.get("duration", 0)
                    word_count = log.get("word_count", 0)
                    ai_chars = log.get("ai_continuation_chars", 0)
                    ai_chats = log.get("ai_chat_count", 0)

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
                        ai_chats
                    ])
            QMessageBox.information(self, "成功", "創作日誌與 AI 數據已成功匯出至 CSV 檔案！")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"匯出時發生錯誤：{e}")

    def close_dashboard(self):
        self.main_window.center_stack.setCurrentIndex(0)

    def update_scale(self, scale: float):
        """依據縮放比例更新儀表板字型、卡片大小與圖表/表格尺寸。"""
        self.scale_factor = scale
        self.lbl_title.setFont(FontManager.get_font(size=int(16 * scale), weight=QFont.Weight.Bold))
        self.btn_share.setFont(FontManager.get_font(size=int(9 * scale)))
        self.btn_export.setFont(FontManager.get_font(size=int(9 * scale)))
        self.btn_close.setFont(FontManager.get_font(size=int(9 * scale)))

        self.card_duration.update_scale(scale)
        self.card_total_words.update_scale(scale)
        self.card_avg_words.update_scale(scale)
        self.card_ai_ratio.update_scale(scale)

        if hasattr(self, "lbl_chart_mode"):
            self.lbl_chart_mode.setFont(FontManager.get_font(size=int(9 * scale)))
        for btn in (self.btn_mode_trend, self.btn_mode_heatmap, self.btn_mode_chapters, self.btn_mode_ai):
            btn.setFont(FontManager.get_font(size=int(9 * scale)))

        if hasattr(self, "chart_view"):
            self.chart_view.set_scale(scale)
            self.chart_view.setMinimumHeight(int(180 * scale))

        if hasattr(self, "table"):
            self.table.setFont(FontManager.get_font(size=int(9 * scale)))
            self.table.horizontalHeader().setFont(FontManager.get_font(size=int(9 * scale), weight=QFont.Weight.Bold))
            self.table.setFixedHeight(int(180 * scale))

