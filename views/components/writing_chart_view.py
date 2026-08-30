import math
import datetime
from PyQt6.QtWidgets import QWidget, QToolTip
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QBrush, QPen, QPainterPath, QLinearGradient
)
from PyQt6.QtCore import Qt, QRectF, QPoint

from utils.font_manager import FontManager

class WritingChartView(QWidget):
    """寫作數據視覺化繪圖元件，支援：字數趨勢折線圖、GitHub 風格每日打卡熱力圖、各章字數長條圖與 AI 介入度分析。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.mode = "trend"  # "trend" | "heatmap" | "chapters" | "ai_ratio"

        # 數據資料
        self.dates = []
        self.values = []
        self.ai_chars = []
        self.ai_chats = []
        self.chapter_names = []
        self.chapter_words = []

        # 熱力圖網格快顯區域快取
        self.heatmap_rects = []  # list of (QRectF, date_str, word_count)

        # 主題色彩
        self.theme_color = QColor("#69f0ae")
        self.glow_color = QColor("#00e676")

    def set_mode(self, mode: str):
        self.mode = mode
        self.update()

    def set_data(self, dates, values, ai_chars=None, ai_chats=None):
        self.dates = dates
        self.values = values
        self.ai_chars = ai_chars if ai_chars is not None else [0] * len(values)
        self.ai_chats = ai_chats if ai_chats is not None else [0] * len(values)
        self.update()

    def set_chapter_stats(self, chapter_names, chapter_words):
        self.chapter_names = chapter_names
        self.chapter_words = chapter_words
        self.update()

    def set_theme_colors(self, main_color, glow_color):
        self.theme_color = main_color
        self.glow_color = glow_color
        self.update()

    def mouseMoveEvent(self, event):
        pos = event.position()
        if self.mode == "heatmap":
            for rect, date_str, count in self.heatmap_rects:
                if rect.contains(pos):
                    QToolTip.showText(event.globalPosition().toPoint(), f"{date_str}：寫作 {count} 字", self)
                    return
            QToolTip.hideText()
        super().mouseMoveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.mode == "trend":
            self._paint_trend(painter)
        elif self.mode == "heatmap":
            self._paint_heatmap(painter)
        elif self.mode == "chapters":
            self._paint_chapters(painter)
        elif self.mode == "ai_ratio":
            self._paint_ai_ratio(painter)

    # =========================================================================
    # 1. 寫作字數趨勢折線圖
    # =========================================================================
    def _paint_trend(self, painter: QPainter):
        w = self.width()
        h = self.height()

        left_pad = 60
        right_pad = 30
        top_pad = 30
        bottom_pad = 40

        graph_w = w - left_pad - right_pad
        graph_h = h - top_pad - bottom_pad

        if graph_w <= 0 or graph_h <= 0:
            return

        grid_pen = QPen(QColor(255, 255, 255, 20), 1, Qt.PenStyle.DashLine)
        text_pen = QPen(QColor(170, 170, 170))
        axis_pen = QPen(QColor(85, 85, 85), 1)

        painter.setPen(axis_pen)
        painter.drawRect(left_pad, top_pad, graph_w, graph_h)

        if not self.values or len(self.values) == 0:
            painter.setPen(text_pen)
            painter.setFont(FontManager.get_font(size=10))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "尚無寫作字數數據")
            return

        max_val = max(self.values)
        if max_val <= 0:
            max_val = 1000
        else:
            max_val = int(max_val * 1.2)

        # Y 軸刻度與格線
        painter.setFont(FontManager.get_font(size=8))
        for i in range(5):
            val = int(max_val * i / 4)
            y = top_pad + graph_h - int(i * graph_h / 4)
            if 0 < i < 4:
                painter.setPen(grid_pen)
                painter.drawLine(left_pad, y, left_pad + graph_w, y)
            painter.setPen(text_pen)
            painter.drawText(5, y - 10, left_pad - 10, 20, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, str(val))

        # X 軸刻度
        num_points = len(self.values)
        x_coords = []
        y_coords = []
        dx = graph_w / (num_points - 1) if num_points > 1 else graph_w

        for i in range(num_points):
            x = left_pad + int(i * dx) if num_points > 1 else left_pad + int(graph_w / 2)
            y = top_pad + graph_h - int((self.values[i] / max_val) * graph_h)
            x_coords.append(x)
            y_coords.append(y)

            if 0 < i < num_points - 1:
                painter.setPen(grid_pen)
                painter.drawLine(x, top_pad, x, top_pad + graph_h)

            date_str = self.dates[i]
            if len(date_str) > 5 and "-" in date_str:
                parts = date_str.split("-")
                if len(parts) >= 3:
                    date_str = f"{parts[1]}-{parts[2]}"
            painter.setPen(text_pen)
            painter.drawText(x - 30, top_pad + graph_h + 5, 60, 20, Qt.AlignmentFlag.AlignCenter, date_str)

        # 漸層填滿
        if num_points > 1:
            path_fill = QPainterPath()
            path_fill.moveTo(x_coords[0], top_pad + graph_h)
            for i in range(num_points):
                path_fill.lineTo(x_coords[i], y_coords[i])
            path_fill.lineTo(x_coords[-1], top_pad + graph_h)
            path_fill.closeSubpath()

            grad = QLinearGradient(0, top_pad, 0, top_pad + graph_h)
            grad.setColorAt(0.0, QColor(self.theme_color.red(), self.theme_color.green(), self.theme_color.blue(), 70))
            grad.setColorAt(1.0, QColor(self.theme_color.red(), self.theme_color.green(), self.theme_color.blue(), 5))
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(path_fill)

        # 主折線與圓點
        if num_points > 1:
            path_line = QPainterPath()
            path_line.moveTo(x_coords[0], y_coords[0])
            for i in range(1, num_points):
                path_line.lineTo(x_coords[i], y_coords[i])
            painter.setPen(QPen(self.theme_color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path_line)

        painter.setPen(QPen(self.theme_color, 2))
        painter.setBrush(QBrush(QColor("#1e1e1e")))
        for i in range(num_points):
            painter.drawEllipse(x_coords[i] - 4, y_coords[i] - 4, 8, 8)

    # =========================================================================
    # 2. GitHub Contribution 風格「每日打卡熱力圖」
    # =========================================================================
    def _paint_heatmap(self, painter: QPainter):
        w = self.width()
        h = self.height()
        self.heatmap_rects.clear()

        painter.setFont(FontManager.get_font(size=9))
        text_pen = QPen(QColor(170, 170, 170))

        # 標題
        painter.setPen(text_pen)
        painter.drawText(20, 20, 300, 20, Qt.AlignmentFlag.AlignLeft, "📅 寫作打卡熱力圖（近 24 週）")

        # 建立日期與字數查找表
        date_map = {d: v for d, v in zip(self.dates, self.values)}

        # 計算近 24 週（約 168 天）
        today = datetime.date.today()
        # 找到最近一個週六作為結尾
        days_to_sat = (5 - today.weekday()) % 7
        end_date = today + datetime.timedelta(days=days_to_sat)
        start_date = end_date - datetime.timedelta(weeks=24, days=6)

        weeks = 24
        days_per_week = 7

        box_size = max(10, min(16, int((w - 80) / weeks) - 3))
        spacing = 3

        start_x = 45
        start_y = 50

        # 繪製星期標籤 (Mon, Wed, Fri)
        day_labels = ["一", "二", "三", "四", "五", "六", "日"]
        painter.setFont(FontManager.get_font(size=8))
        for day_idx in [0, 2, 4]:
            painter.setPen(text_pen)
            painter.drawText(10, start_y + day_idx * (box_size + spacing) + box_size - 2, 30, 16, Qt.AlignmentFlag.AlignRight, day_labels[day_idx])

        # 繪製打卡方塊
        curr_date = start_date
        for col in range(weeks):
            for row in range(days_per_week):
                d_str = curr_date.strftime("%Y-%m-%d")
                count = date_map.get(d_str, 0)

                # 依字數決定顏色深度
                if count <= 0:
                    bg_color = QColor(255, 255, 255, 12)
                elif count < 500:
                    bg_color = QColor(self.theme_color.red(), self.theme_color.green(), self.theme_color.blue(), 80)
                elif count < 1500:
                    bg_color = QColor(self.theme_color.red(), self.theme_color.green(), self.theme_color.blue(), 140)
                elif count < 3000:
                    bg_color = QColor(self.theme_color.red(), self.theme_color.green(), self.theme_color.blue(), 200)
                else:
                    bg_color = self.theme_color

                rect = QRectF(start_x + col * (box_size + spacing), start_y + row * (box_size + spacing), box_size, box_size)
                self.heatmap_rects.append((rect, d_str, count))

                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(bg_color))
                painter.drawRoundedRect(rect, 2, 2)

                curr_date += datetime.timedelta(days=1)

        # 圖例
        legend_y = start_y + days_per_week * (box_size + spacing) + 15
        painter.setPen(text_pen)
        painter.drawText(start_x, legend_y, 40, 20, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "少")
        
        levels = [
            QColor(255, 255, 255, 12),
            QColor(self.theme_color.red(), self.theme_color.green(), self.theme_color.blue(), 80),
            QColor(self.theme_color.red(), self.theme_color.green(), self.theme_color.blue(), 140),
            QColor(self.theme_color.red(), self.theme_color.green(), self.theme_color.blue(), 200),
            self.theme_color
        ]
        leg_x = start_x + 30
        for lvl_color in levels:
            painter.setBrush(QBrush(lvl_color))
            painter.drawRoundedRect(QRectF(leg_x, legend_y + 3, 12, 12), 2, 2)
            leg_x += 16
        painter.setPen(text_pen)
        painter.drawText(leg_x + 4, legend_y, 40, 20, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "多")

    # =========================================================================
    # 3. 全書各章字數長條圖
    # =========================================================================
    def _paint_chapters(self, painter: QPainter):
        w = self.width()
        h = self.height()

        left_pad = 120
        right_pad = 40
        top_pad = 30
        bottom_pad = 20

        text_pen = QPen(QColor(170, 170, 170))
        painter.setFont(FontManager.get_font(size=9))

        if not self.chapter_words or len(self.chapter_words) == 0:
            painter.setPen(text_pen)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "尚未建立任何章節或章節尚無字數")
            return

        max_val = max(self.chapter_words) if max(self.chapter_words) > 0 else 1000
        bar_height = max(16, min(28, int((h - top_pad - bottom_pad) / len(self.chapter_words)) - 6))
        spacing = 6
        avail_w = w - left_pad - right_pad - 60

        painter.setPen(text_pen)
        painter.drawText(20, 15, 300, 20, Qt.AlignmentFlag.AlignLeft, "📊 全書各章節字數分佈圖")

        for idx, (name, count) in enumerate(zip(self.chapter_names, self.chapter_words)):
            y = top_pad + idx * (bar_height + spacing)
            if y + bar_height > h - bottom_pad:
                break

            # 章節名稱（截斷）
            display_name = name[:10] + ("..." if len(name) > 10 else "")
            painter.setPen(text_pen)
            painter.drawText(10, y, left_pad - 20, bar_height, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, display_name)

            # 長條
            bar_w = int((count / max_val) * avail_w) if max_val > 0 else 0
            bar_rect = QRectF(left_pad, y + 2, max(4, bar_w), bar_height - 4)

            grad = QLinearGradient(left_pad, 0, left_pad + bar_w, 0)
            grad.setColorAt(0.0, QColor(self.theme_color.red(), self.theme_color.green(), self.theme_color.blue(), 160))
            grad.setColorAt(1.0, self.theme_color)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(bar_rect, 3, 3)

            # 字數標記
            painter.setPen(text_pen)
            painter.drawText(left_pad + bar_w + 8, y, 60, bar_height, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{count} 字")

    # =========================================================================
    # 4. AI 介入度與原創字數分析圖
    # =========================================================================
    def _paint_ai_ratio(self, painter: QPainter):
        w = self.width()
        h = self.height()

        text_pen = QPen(QColor(170, 170, 170))
        painter.setFont(FontManager.get_font(size=9))

        total_words = sum(self.values)
        total_ai_chars = sum(self.ai_chars)
        total_ai_chats = sum(self.ai_chats)
        total_manual_words = max(0, total_words - total_ai_chars)

        painter.setPen(text_pen)
        painter.drawText(20, 20, 300, 20, Qt.AlignmentFlag.AlignLeft, "🤖 AI 創作介入度與輔助比例分析")

        if total_words <= 0 and total_ai_chars <= 0:
            painter.setPen(text_pen)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "尚未累積足夠的寫作與 AI 互動記錄")
            return

        # 圓餅圖/環形圖繪製
        center_x = int(w * 0.35)
        center_y = int(h * 0.55)
        radius = min(int(h * 0.32), 90)

        pie_total = max(1, total_manual_words + total_ai_chars)
        manual_angle = int((total_manual_words / pie_total) * 360 * 16)
        ai_angle = 360 * 16 - manual_angle

        manual_color = self.theme_color
        ai_color = QColor("#00a8cc") if self.theme_color != QColor("#00a8cc") else QColor("#ff9800")

        # 繪製手寫原創扇區
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(manual_color))
        painter.drawPie(center_x - radius, center_y - radius, radius * 2, radius * 2, 0, manual_angle)

        # 繪製 AI 續寫扇區
        if total_ai_chars > 0:
            painter.setBrush(QBrush(ai_color))
            painter.drawPie(center_x - radius, center_y - radius, radius * 2, radius * 2, manual_angle, ai_angle)

        # 內圈中空環形
        inner_r = int(radius * 0.6)
        painter.setBrush(QBrush(QColor("#1e1e1e")))
        painter.drawEllipse(center_x - inner_r, center_y - inner_r, inner_r * 2, inner_r * 2)

        # 環形中間文字
        ratio_pct = int((total_ai_chars / pie_total) * 100)
        painter.setPen(text_pen)
        painter.setFont(FontManager.get_font(size=11, weight=QFont.Weight.Bold))
        painter.drawText(center_x - inner_r, center_y - 10, inner_r * 2, 20, Qt.AlignmentFlag.AlignCenter, f"{ratio_pct}%")
        painter.setFont(FontManager.get_font(size=8))
        painter.drawText(center_x - inner_r, center_y + 8, inner_r * 2, 16, Qt.AlignmentFlag.AlignCenter, "AI 輔助")

        # 右側數據統計明細
        info_x = int(w * 0.6)
        info_y = center_y - 70

        painter.setFont(FontManager.get_font(size=10, weight=QFont.Weight.Bold))
        painter.setPen(text_pen)
        painter.drawText(info_x, info_y, 250, 24, Qt.AlignmentFlag.AlignLeft, "數據明細總覽：")

        # 項目 1：手寫原創字數
        painter.setBrush(QBrush(manual_color))
        painter.drawRoundedRect(QRectF(info_x, info_y + 35, 12, 12), 2, 2)
        painter.setFont(FontManager.get_font(size=9))
        painter.setPen(text_pen)
        painter.drawText(info_x + 20, info_y + 30, 220, 20, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"手寫原創字數：{total_manual_words:,} 字 ({100 - ratio_pct}%)")

        # 項目 2：AI 續寫字數
        painter.setBrush(QBrush(ai_color))
        painter.drawRoundedRect(QRectF(info_x, info_y + 65, 12, 12), 2, 2)
        painter.drawText(info_x + 20, info_y + 60, 220, 20, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"AI 續寫字數：{total_ai_chars:,} 字 ({ratio_pct}%)")

        # 項目 3：AI 對話互動
        painter.setBrush(QBrush(QColor("#ab47bc")))
        painter.drawRoundedRect(QRectF(info_x, info_y + 95, 12, 12), 2, 2)
        painter.drawText(info_x + 20, info_y + 90, 220, 20, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"AI 對話與分析互動：{total_ai_chats:,} 次")
