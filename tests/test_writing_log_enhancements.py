import os
import tempfile
import unittest
import sqlite3
import datetime
from PyQt6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import Qt
from models.models import JneProject, WritingLogEntry, ChapterNode
from services.database import DatabaseService
from services.database_migrations import DatabaseMigrations
from controllers.stats_controller import StatsController
from views.components.writing_chart_view import WritingChartView
from views.components.writing_log_dashboard import WritingLogDashboard
from views.components.jne_text_edit import JNE_TextEdit

app = QApplication.instance() or QApplication([])

class DummyTreeController:
    def is_item_valid(self, item):
        return item is not None
    def get_item_id(self, item):
        return "item-123"

class DummyMainController:
    def __init__(self):
        self.writing_logs = []
        self.today_written_count = 0
        self.active_session = None
        self.last_known_word_count = 0
        self.file_word_stats = {}
        self.tree = DummyTreeController()
        self.current_file_item = QTreeWidgetItem(["第一章"])
        self.current_file_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "file", "id": "item-123", "content": "原始內容"})

    def save_temp_doc(self):
        pass

    def save_current_editor_content(self):
        pass

    def update_status_bar(self):
        pass

    def mark_dirty(self, dirty=True):
        pass

    def get_writing_logs_as_dict(self):
        return [
            {
                "date": log.date,
                "duration": log.duration,
                "word_count": log.word_count,
                "ai_continuation_count": getattr(log, "ai_continuation_count", 0),
                "ai_continuation_chars": getattr(log, "ai_continuation_chars", 0),
                "ai_chat_count": getattr(log, "ai_chat_count", 0),
                "ai_details": dict(getattr(log, "ai_details", {})),
                "paste_large_count": getattr(log, "paste_large_count", 0),
                "delete_large_count": getattr(log, "delete_large_count", 0)
            }
            for log in self.writing_logs
        ]

class DummyView:
    def __init__(self):
        self.editor = JNE_TextEdit()
        self.writing_log_dashboard = None

class TestWritingLogEnhancements(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_enhancements.jne")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_database_migration_v12_and_roundtrip(self):
        """驗證 v11 升級至 v12 增加 paste_large_count 與 delete_large_count，並驗證儲存與載入。"""
        DatabaseService.init_db(self.db_path)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        v = DatabaseMigrations.get_current_schema_version(cursor)
        self.assertEqual(v, 12)

        cursor.execute("PRAGMA table_info(writing_logs)")
        cols = {row[1] for row in cursor.fetchall()}
        self.assertIn("paste_large_count", cols)
        self.assertIn("delete_large_count", cols)
        conn.close()

        # 儲存包含大量貼上與刪除的寫作日誌
        proj = JneProject()
        proj.writing_logs.append(WritingLogEntry(
            date="2026-09-04",
            duration=600,
            word_count=1200,
            paste_large_count=3,
            delete_large_count=2
        ))
        DatabaseService.save_project(proj, self.db_path)

        # 讀取並驗證
        loaded = DatabaseService.load_project(self.db_path)
        self.assertEqual(len(loaded.writing_logs), 1)
        log = loaded.writing_logs[0]
        self.assertEqual(log.date, "2026-09-04")
        self.assertEqual(log.paste_large_count, 3)
        self.assertEqual(log.delete_large_count, 2)

    def test_large_paste_detection(self):
        """驗證短時間內貼上超過300字觸發大量貼上記錄。"""
        mc = DummyMainController()
        view = DummyView()
        mc.view = view
        stats = StatsController(mc)
        mc.stats = stats

        today_str = datetime.datetime.now().strftime("%Y-%m-%d")

        # 貼上小於 300 字：不應累計
        small_text = "這是一段簡短的文字貼上。" * 5
        stats.on_text_pasted(small_text)
        self.assertEqual(len(mc.writing_logs), 0)

        # 貼上大於 300 字：應累計 1 次
        large_text = "這是一段長篇小說內文測試段落。" * 30  # 約 450 字
        stats.on_text_pasted(large_text)
        self.assertEqual(len(mc.writing_logs), 1)
        self.assertEqual(mc.writing_logs[0].date, today_str)
        self.assertEqual(mc.writing_logs[0].paste_large_count, 1)

    def test_large_delete_detection(self):
        """驗證短時間內刪除超過300字觸發大量刪除記錄。"""
        mc = DummyMainController()
        view = DummyView()
        mc.view = view
        stats = StatsController(mc)
        mc.stats = stats

        today_str = datetime.datetime.now().strftime("%Y-%m-%d")

        # 正常打字退格（刪除少數字元）：不應累計
        stats.on_document_contents_change(0, charsRemoved=1, charsAdded=0)
        self.assertEqual(len(mc.writing_logs), 0)

        # 單次大範圍反白刪除（例如刪除 350 字元）
        stats.on_document_contents_change(0, charsRemoved=350, charsAdded=0)
        self.assertEqual(len(mc.writing_logs), 1)
        self.assertEqual(mc.writing_logs[0].date, today_str)
        self.assertEqual(mc.writing_logs[0].delete_large_count, 1)

    def test_heatmap_dates_include_today(self):
        """驗證熱力圖週對齊算法能精準涵蓋今日（如2026-09-04）及過去24週所有日期。"""
        chart = WritingChartView()
        today = datetime.date.today()
        today_str = today.strftime("%Y-%m-%d")

        # 傳入包含今日與數天前的資料
        full_dates = {today_str: 652}
        chart.set_data(
            dates=[today_str],
            values=[652],
            full_date_map=full_dates
        )

        chart.resize(800, 250)
        # 觸發繪圖以生成 heatmap_rects
        from PyQt6.QtGui import QPainter, QPixmap
        pixmap = QPixmap(800, 250)
        painter = QPainter(pixmap)
        chart._paint_heatmap(painter)
        painter.end()

        # 檢查 heatmap_rects 中是否存在今日與字數
        rect_dates = [d for _, d, _ in chart.heatmap_rects]
        self.assertIn(today_str, rect_dates)
        today_entry = next((item for item in chart.heatmap_rects if item[1] == today_str), None)
        self.assertIsNotNone(today_entry)
        self.assertEqual(today_entry[2], 652)

    def test_chapter_stats_extraction(self):
        """驗證 WritingLogDashboard._extract_chapter_stats 能正確讀取 type=file 節點字數。"""
        class MockMainWindow:
            def __init__(self):
                self.tree_widget = QTreeWidget()
                self.writing_logs = []
                self.current_theme = "default"
                # 建立第一章與第二章節點 (type="file")
                item1 = QTreeWidgetItem(["第一章 風起"])
                item1.setData(0, Qt.ItemDataRole.UserRole, {"type": "file", "content": "這是第一章的測試內容。" * 20})
                self.tree_widget.addTopLevelItem(item1)

                item2 = QTreeWidgetItem(["第二章 雲湧"])
                item2.setData(0, Qt.ItemDataRole.UserRole, {"type": "file", "content": "這是第二章的測試內容。" * 10})
                self.tree_widget.addTopLevelItem(item2)

        win = MockMainWindow()
        dashboard = WritingLogDashboard(win)
        names, words = dashboard._extract_chapter_stats()

        self.assertEqual(len(names), 2)
        self.assertEqual(names[0], "第一章 風起")
        self.assertEqual(names[1], "第二章 雲湧")
        self.assertGreater(words[0], words[1])
        self.assertGreater(words[1], 0)

    def test_ai_ratio_chart_excludes_paste_and_delete(self):
        """驗證 AI 介入度分析圖與誠信卡片中，大量貼上與刪除行為不列入 AI 誠信光譜指標。"""
        from PyQt6.QtGui import QPainter, QPixmap
        chart = WritingChartView()
        chart.set_data(
            dates=["2026-09-04"],
            values=[1000],
            ai_chars=[200],
            ai_chats=[3],
            ai_details=[{"proofread": 1, "chat": 2}],
            total_paste_large=5,
            total_delete_large=3
        )
        chart.resize(800, 300)

        # 模擬繪製 _paint_ai_ratio，驗證繪製過程無例外且各面向正確處理
        pixmap = QPixmap(800, 300)
        painter = QPainter(pixmap)
        chart._paint_ai_ratio(painter)
        painter.end()

        # 驗證 WritingLogDashboard 的 card_ai_ratio 副標題不包含貼上/刪除字樣
        class MockMainWindow:
            def __init__(self):
                self.tree_widget = QTreeWidget()
                self.writing_logs = []
                self.current_theme = "default"
                self.scale_factor = 1.0

        win = MockMainWindow()
        dashboard = WritingLogDashboard(win)
        dashboard.refresh_data([{
            "date": "2026-09-04",
            "duration": 1800,
            "word_count": 1000,
            "ai_continuation_chars": 200,
            "ai_chat_count": 3,
            "ai_details": {"proofread": 1, "chat": 2},
            "paste_large_count": 5,
            "delete_large_count": 3
        }])

        sub_text = dashboard.card_ai_ratio.lbl_sub.text()
        self.assertNotIn("異動", sub_text)
        self.assertNotIn("貼5", sub_text)
        self.assertNotIn("刪3", sub_text)

    def test_writing_log_dashboard_ui_scale_response(self):
        """驗證創作日誌文字與介面依據全局介面 % 數做相應縮放反應。"""
        class MockMainWindow:
            def __init__(self):
                self.tree_widget = QTreeWidget()
                self.writing_logs = []
                self.current_theme = "default"
                self.scale_factor = 1.0

        win = MockMainWindow()
        dashboard = WritingLogDashboard(win)

        # 縮放到 1.5 (150%)
        dashboard.update_scale(1.5)
        self.assertEqual(dashboard.scale_factor, 1.5)
        self.assertEqual(dashboard.chart_view.scale_factor, 1.5)
        self.assertEqual(dashboard.lbl_title.font().pointSize(), int(16 * 1.5))
        self.assertEqual(dashboard.card_duration.lbl_val.font().pointSize(), int(14 * 1.5))
        self.assertEqual(dashboard.chart_view.minimumHeight(), max(180, int(200 * 1.5)))
        self.assertEqual(dashboard.table.height(), max(160, int(190 * 1.5)))

        # 縮放到 2.0 (200%)
        dashboard.update_scale(2.0)
        self.assertEqual(dashboard.scale_factor, 2.0)
        self.assertEqual(dashboard.chart_view.scale_factor, 2.0)
        self.assertEqual(dashboard.lbl_title.font().pointSize(), int(16 * 2.0))
        self.assertEqual(dashboard.card_duration.lbl_val.font().pointSize(), int(14 * 2.0))
        self.assertEqual(dashboard.chart_view.minimumHeight(), int(200 * 2.0))
        self.assertEqual(dashboard.table.height(), int(190 * 2.0))

if __name__ == "__main__":
    unittest.main()
