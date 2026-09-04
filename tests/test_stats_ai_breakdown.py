import os
import tempfile
import unittest
import sqlite3
import datetime
from PyQt6.QtWidgets import QApplication
from models.models import JneProject, WritingLogEntry
from services.database import DatabaseService
from services.database_migrations import DatabaseMigrations
from controllers.stats_controller import StatsController

# 確保 QApplication 存在供 UI 元件或相關類別使用
app = QApplication.instance() or QApplication([])

class DummyMainWindow:
    def __init__(self):
        self.writing_logs = []
        self.today_written_count = 0
        self.active_session = None

    def save_temp_doc(self):
        pass

    def save_current_editor_content(self):
        pass

    def update_status_bar(self):
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
                "ai_details": dict(getattr(log, "ai_details", {}))
            }
            for log in self.writing_logs
        ]

class DummyView:
    def __init__(self):
        pass

class TestStatsAiBreakdown(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_project.jne")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_record_ai_activity_with_feature_keys(self):
        """驗證 StatsController.record_ai_activity 能正確記錄各種 feature_key。"""
        mc = DummyMainWindow()
        mc.view = DummyView()
        stats = StatsController(mc)

        # 模擬呼叫對話、角色提取、AI 校稿、正文擴寫
        stats.record_ai_activity(chat_count=1, feature_key="chat")
        stats.record_ai_activity(chat_count=1, feature_key="character")
        stats.record_ai_activity(chat_count=1, feature_key="proofread")
        stats.record_ai_activity(continuation_count=1, continuation_chars=120, feature_key="continuation")

        self.assertEqual(len(mc.writing_logs), 1)
        today_log = mc.writing_logs[0]
        self.assertEqual(today_log.ai_chat_count, 3)
        self.assertEqual(today_log.ai_continuation_count, 1)
        self.assertEqual(today_log.ai_continuation_chars, 120)

        # 驗證 ai_details 內容
        self.assertEqual(today_log.ai_details.get("chat"), 1)
        self.assertEqual(today_log.ai_details.get("character"), 1)
        self.assertEqual(today_log.ai_details.get("proofread"), 1)
        self.assertEqual(today_log.ai_details.get("continuation"), 1)

    def test_database_save_and_load_ai_details(self):
        """驗證資料庫儲存與讀取 WritingLogEntry 的 ai_details 字典。"""
        DatabaseService.init_db(self.db_path)
        project = JneProject()
        project.writing_logs.append(WritingLogEntry(
            date="2026-09-04",
            duration=3600,
            word_count=2000,
            ai_continuation_count=1,
            ai_continuation_chars=300,
            ai_chat_count=5,
            ai_details={
                "chat": 2,
                "character": 1,
                "world": 1,
                "proofread": 1
            }
        ))
        DatabaseService.save_project(project, self.db_path)

        # 重新讀取
        loaded = DatabaseService.load_project(self.db_path)
        self.assertEqual(len(loaded.writing_logs), 1)
        log = loaded.writing_logs[0]
        self.assertEqual(log.date, "2026-09-04")
        self.assertEqual(log.ai_details.get("chat"), 2)
        self.assertEqual(log.ai_details.get("character"), 1)
        self.assertEqual(log.ai_details.get("world"), 1)
        self.assertEqual(log.ai_details.get("proofread"), 1)

    def test_migration_v10_to_v11(self):
        """驗證資料庫遷移能將舊表自動增加 ai_details 欄位。"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # 建立 v10 的舊 writing_logs 表 (無 ai_details 欄位)
        cursor.execute('''
            CREATE TABLE writing_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                duration INTEGER,
                word_count INTEGER,
                ai_continuation_count INTEGER DEFAULT 0,
                ai_continuation_chars INTEGER DEFAULT 0,
                ai_chat_count INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT
            )
        ''')
        cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (10, '2026-09-01 00:00:00')")
        conn.commit()

        # 執行升級
        DatabaseMigrations.apply_migrations(cursor)
        conn.commit()

        try:
            cursor.execute("PRAGMA table_info(writing_logs)")
            cols = {row[1] for row in cursor.fetchall()}
            self.assertIn("ai_details", cols)

            cursor.execute("SELECT MAX(version) FROM schema_version")
            curr_v = cursor.fetchone()[0]
            self.assertGreaterEqual(curr_v, 11)
        finally:
            conn.close()

if __name__ == "__main__":
    unittest.main()
