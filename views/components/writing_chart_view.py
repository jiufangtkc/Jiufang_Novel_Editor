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
        self.ai_details = []
        self.full_date_map = {}
        self.total_paste_large = 0
        self.total_delete_large = 0
        self.chapter_names = []
        self.chapter_words = []

        # 熱力圖網格快顯區域快取
        self.heatmap_rects = []  # list of (QRectF, date_str, word_count)

        # 主題色彩
        self.theme_color = QColor("#69f0ae")
        self.glow_color = QColor("#00e676")
        self.scale_factor = 1.0

    def set_scale(self, scale: float):
        self.scale_factor = scale
        self.update()

    def set_mode(self, mode: str):
        self.mode = mode
        self.update()

    def set_data(self, dates, values, ai_chars=None, ai_chats=None, ai_details=None, full_date_map=None, total_paste_large=0, total_delete_large=0):
        self.dates = dates
        self.values = values
        self.ai_chars = ai_chars if ai_chars is not None else [0] * len(values)
        self.ai_chats = ai_chats if ai_chats is not None else [0] * len(values)
        self.ai_details = ai_details if ai_details is not None else [{}] * len(values)
        self.full_date_map = full_date_map if full_date_map is not None else {d: v for d, v in zip(dates, values)}
        self.total_paste_large = total_paste_large
        self.total_delete_large = total_delete_large
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

        left_pad = int(60 * self.scale_factor)
        right_pad = int(30 * self.scale_factor)
        top_pad = int(30 * self.scale_factor)
        bottom_pad = int(40 * self.scale_factor)

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
            painter.setFont(FontManager.get_font(size=int(10 * self.scale_factor)))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "尚無寫作字數數據")
            return

        max_val = max(self.values)
        if max_val <= 0:
            max_val = 1000
        else:
            max_val = int(max_val * 1.2)

        # Y 軸刻度與格線
        painter.setFont(FontManager.get_font(size=int(8 * self.scale_factor)))
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
            painter.setPen(QPen(self.theme_color, max(1, int(2 * self.scale_factor))))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path_line)

        dot_r = max(3, int(4 * self.scale_factor))
        painter.setPen(QPen(self.theme_color, max(1, int(2 * self.scale_factor))))
        painter.setBrush(QBrush(QColor("#1e1e1e")))
        for i in range(num_points):
            painter.drawEllipse(x_coords[i] - dot_r, y_coords[i] - dot_r, dot_r * 2, dot_r * 2)

    # =========================================================================
    # 2. GitHub Contribution 風格「每日打卡熱力圖」
    # =========================================================================
    def _paint_heatmap(self, painter: QPainter):
        w = self.width()
        h = self.height()
        scale = getattr(self, "scale_factor", 1.0)
        self.heatmap_rects.clear()

        painter.setFont(FontManager.get_font(size=max(8, int(10 * scale)), weight=QFont.Weight.Bold))
        text_pen = QPen(QColor(170, 170, 170))

        # 標題
        painter.setPen(text_pen)
        painter.drawText(int(20 * scale), int(12 * scale), int(350 * scale), int(22 * scale), Qt.AlignmentFlag.AlignLeft, "📅 寫作打卡熱力圖（近 24 週）")

        # 建立全量日期與字數查找表
        date_map = self.full_date_map if self.full_date_map else {d: v for d, v in zip(self.dates, self.values)}

        today = datetime.date.today()
        curr_monday = today - datetime.timedelta(days=today.weekday())
        start_date = curr_monday - datetime.timedelta(weeks=23)

        weeks = 24
        days_per_week = 7

        spacing = max(2, int(3 * scale))
        start_x = int(45 * scale)
        start_y = int(40 * scale)
        box_size = max(int(10 * scale), min(int(18 * scale), int((w - start_x - int(30 * scale)) / weeks) - spacing))

        # 繪製星期標籤 (Mon, Wed, Fri)
        day_labels = ["一", "二", "三", "四", "五", "六", "日"]
        painter.setFont(FontManager.get_font(size=max(7, int(8 * scale))))
        for day_idx in [0, 2, 4]:
            painter.setPen(text_pen)
            painter.drawText(int(5 * scale), start_y + day_idx * (box_size + spacing) + int(2 * scale), start_x - int(10 * scale), box_size, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, day_labels[day_idx])

        # 繪製打卡方塊
        for col in range(weeks):
            for row in range(days_per_week):
                curr_date = start_date + datetime.timedelta(days=col * 7 + row)
                d_str = curr_date.strftime("%Y-%m-%d")
                count = date_map.get(d_str, 0)
                is_future = curr_date > today

                # 依字數或未來日期決定顏色深度
                if is_future:
                    bg_color = QColor(255, 255, 255, 5)
                elif count <= 0:
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
                if not is_future:
                    self.heatmap_rects.append((rect, d_str, count))

                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(bg_color))
                painter.drawRoundedRect(rect, 2, 2)

        # 圖例
        legend_y = start_y + days_per_week * (box_size + spacing) + int(12 * scale)
        painter.setFont(FontManager.get_font(size=max(7, int(8 * scale))))
        painter.setPen(text_pen)
        painter.drawText(start_x, legend_y, int(30 * scale), int(20 * scale), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "少")
        
        levels = [
            QColor(255, 255, 255, 12),
            QColor(self.theme_color.red(), self.theme_color.green(), self.theme_color.blue(), 80),
            QColor(self.theme_color.red(), self.theme_color.green(), self.theme_color.blue(), 140),
            QColor(self.theme_color.red(), self.theme_color.green(), self.theme_color.blue(), 200),
            self.theme_color
        ]
        leg_box = max(8, int(12 * scale))
        leg_step = leg_box + max(3, int(4 * scale))
        leg_x = start_x + int(24 * scale)
        for lvl_color in levels:
            painter.setBrush(QBrush(lvl_color))
            painter.drawRoundedRect(QRectF(leg_x, legend_y + int(3 * scale), leg_box, leg_box), 2, 2)
            leg_x += leg_step
        painter.setPen(text_pen)
        painter.drawText(leg_x + int(4 * scale), legend_y, int(30 * scale), int(20 * scale), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "多")

    # =========================================================================
    # 3. 全書各章字數長條圖
    # =========================================================================
    def _paint_chapters(self, painter: QPainter):
        w = self.width()
        h = self.height()
        scale = getattr(self, "scale_factor", 1.0)

        left_pad = int(120 * scale)
        right_pad = int(40 * scale)
        top_pad = int(35 * scale)
        bottom_pad = int(20 * scale)

        text_pen = QPen(QColor(170, 170, 170))
        painter.setFont(FontManager.get_font(size=max(7, int(9 * scale))))

        if not self.chapter_words or len(self.chapter_words) == 0:
            painter.setPen(text_pen)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "尚未建立任何章節或章節尚無字數")
            return

        max_val = max(self.chapter_words) if max(self.chapter_words) > 0 else 1000
        total_ch = len(self.chapter_words)
        spacing = max(3, int((4 if total_ch > 15 else 6) * scale))
        avail_h = h - top_pad - bottom_pad
        bar_height = max(int(10 * scale), min(int(26 * scale), int(avail_h / total_ch) - spacing))
        avail_w = w - left_pad - right_pad - int(60 * scale)

        painter.setPen(text_pen)
        painter.setFont(FontManager.get_font(size=max(8, int(10 * scale)), weight=QFont.Weight.Bold))
        painter.drawText(int(20 * scale), int(12 * scale), int(380 * scale), int(22 * scale), Qt.AlignmentFlag.AlignLeft, f"📊 全書各章節字數分佈圖（共 {total_ch} 章）")

        font_label = FontManager.get_font(size=max(7, int(8.5 * scale)))
        font_count = FontManager.get_font(size=max(7, int(8 * scale)))

        for idx, (name, count) in enumerate(zip(self.chapter_names, self.chapter_words)):
            y = top_pad + idx * (bar_height + spacing)
            if y + bar_height > h - bottom_pad:
                break

            # 章節名稱（截斷）
            display_name = name[:10] + ("..." if len(name) > 10 else "")
            painter.setFont(font_label)
            painter.setPen(text_pen)
            painter.drawText(int(10 * scale), y, left_pad - int(20 * scale), bar_height, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, display_name)

            # 長條
            bar_w = int((count / max_val) * avail_w) if max_val > 0 else 0
            bar_rect = QRectF(left_pad, y + int(2 * scale), max(4, bar_w), bar_height - int(4 * scale))

            grad = QLinearGradient(left_pad, 0, left_pad + bar_w, 0)
            grad.setColorAt(0.0, QColor(self.theme_color.red(), self.theme_color.green(), self.theme_color.blue(), 160))
            grad.setColorAt(1.0, self.theme_color)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(bar_rect, 3, 3)

            # 字數標記
            painter.setFont(font_count)
            painter.setPen(text_pen)
            painter.drawText(left_pad + bar_w + int(8 * scale), y, int(70 * scale), bar_height, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{count} 字")

    # =========================================================================
    # 4. AI 介入度與原創字數分析圖
    # =========================================================================
    def _paint_ai_ratio(self, painter: QPainter):
        w = self.width()
        h = self.height()
        scale = getattr(self, "scale_factor", 1.0)

        text_pen = QPen(QColor(170, 170, 170))
        painter.setFont(FontManager.get_font(size=max(7, int(9 * scale))))

        total_words = sum(self.values)
        total_ai_chars = sum(self.ai_chars)
        total_ai_chats = sum(self.ai_chats)
        total_manual_words = max(0, total_words - total_ai_chars)

        # 計算細部面向
        structuring_count = 0
        editorial_count = 0
        brainstorming_count = 0
        for d in self.ai_details:
            if isinstance(d, dict):
                structuring_count += d.get("character", 0) + d.get("world", 0) + d.get("timeline", 0)
                editorial_count += d.get("proofread", 0) + d.get("impression", 0)
                brainstorming_count += d.get("chat", 0)
        if structuring_count == 0 and editorial_count == 0 and brainstorming_count == 0:
            brainstorming_count = total_ai_chats

        painter.setPen(text_pen)
        painter.setFont(FontManager.get_font(size=max(8, int(10 * scale)), weight=QFont.Weight.Bold))
        painter.drawText(int(20 * scale), int(20 * scale), int(380 * scale), int(22 * scale), Qt.AlignmentFlag.AlignLeft, "🛡️ AI 創作誠信度與輔助面向分析")

        if total_words <= 0 and total_ai_chars <= 0:
            painter.setFont(FontManager.get_font(size=max(7, int(9 * scale))))
            painter.setPen(text_pen)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "尚未累積足夠的寫作與 AI 互動記錄")
            return

        # 圓餅圖/環形圖繪製
        center_x = int(w * 0.30)
        center_y = int(h * 0.55)
        radius = min(int(h * 0.36), int(85 * scale))

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
        inner_r = int(radius * 0.62)
        painter.setBrush(QBrush(QColor("#1e1e1e")))
        painter.drawEllipse(center_x - inner_r, center_y - inner_r, inner_r * 2, inner_r * 2)

        # 環形中間文字 (突顯手寫原創率)
        handcrafted_pct = 100 if pie_total == 0 else int((total_manual_words / pie_total) * 100)
        painter.setPen(text_pen)
        painter.setFont(FontManager.get_font(size=max(8, int(11 * scale)), weight=QFont.Weight.Bold))
        text_num_y = center_y - int(12 * scale)
        text_num_h = int(20 * scale)
        painter.drawText(center_x - inner_r, text_num_y, inner_r * 2, text_num_h, Qt.AlignmentFlag.AlignCenter, f"{handcrafted_pct}%")

        painter.setFont(FontManager.get_font(size=max(7, int(8 * scale))))
        text_sub_y = center_y + int(8 * scale)
        text_sub_h = int(16 * scale)
        painter.drawText(center_x - inner_r, text_sub_y, inner_r * 2, text_sub_h, Qt.AlignmentFlag.AlignCenter, "手寫原創")

        # 右側數據統計明細
        info_x = int(w * 0.52)
        info_y = max(int(35 * scale), center_y - int(65 * scale))

        painter.setFont(FontManager.get_font(size=max(8, int(10 * scale)), weight=QFont.Weight.Bold))
        painter.setPen(text_pen)
        painter.drawText(info_x, info_y, int(320 * scale), int(22 * scale), Qt.AlignmentFlag.AlignLeft, "誠信指標與輔助明細：")

        painter.setFont(FontManager.get_font(size=max(7, int(8.5 * scale))))
        items = [
            (manual_color, f"親筆手創：{total_manual_words:,} 字 ({handcrafted_pct}%)"),
            (ai_color, f"AI 正文代筆：{total_ai_chars:,} 字 ({100 - handcrafted_pct}%)"),
            (QColor("#42a5f5"), f"🧩 設定架構整理：{structuring_count:,} 次 (角色/世界觀/時間線)"),
            (QColor("#ffa726"), f"🔍 責任編輯審校：{editorial_count:,} 次 (AI校稿/寫作建議)"),
            (QColor("#ab47bc"), f"💬 靈感構思對話：{brainstorming_count:,} 次 (對話助手)")
        ]

        row_y = info_y + int(24 * scale)
        sq_size = max(6, int(9 * scale))
        row_height = max(16, int(20 * scale))
        for color, text in items:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(QRectF(info_x, row_y + int(2 * scale), sq_size, sq_size), 2, 2)
            painter.setPen(text_pen)
            painter.drawText(info_x + sq_size + int(6 * scale), row_y, int(350 * scale), row_height, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
            row_y += row_height
