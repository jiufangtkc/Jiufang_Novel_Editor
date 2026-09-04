import os
import sys
import tempfile
import unittest
import datetime
import sqlite3
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QMessageBox
from models.models import JneProject, ProjectInfo, ChapterNode, WritingLogEntry
from services.database import DatabaseService
from services.database_migrations import DatabaseMigrations
from views.main_window import MainWindow
from controllers.main_controller import MainController

# 初始化 QApplication
app = QApplication.instance() or QApplication(sys.argv)


class TestDailyProgressSync(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_sync.db")
        self.view = MainWindow()
        self.mc = MainController(self.view)

    def tearDown(self):
        self.mc.writing_timer.stop()
        self.mc.auto_save_timer.stop()
        self.view.close()
        self.temp_dir.cleanup()

    def test_database_daily_target_persistence(self):
        """驗證 ProjectInfo.daily_target_word_count 在 SQLite 正確儲存與載入。"""
        project = JneProject()
        project.project_info = ProjectInfo(
            title="同步測試專案",
            target_word_count=50000,
            daily_target_word_count=2500
        )
        DatabaseService.save_project(project, self.db_path)

        loaded = DatabaseService.load_project(self.db_path)
        self.assertEqual(loaded.project_info.daily_target_word_count, 2500)
        self.assertEqual(loaded.project_info.target_word_count, 50000)

    def test_database_migration_v9_to_v10(self):
        """驗證 v9 舊資料庫能平滑升級至 v10 並自動為 project_info 補上 daily_target_word_count。"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # 模擬建立 v9 版本的 project_info（缺少 daily_target_word_count 欄位）
        cursor.execute('''
            CREATE TABLE project_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                logline TEXT,
                current_theme TEXT,
                global_font_family TEXT,
                global_font_size INTEGER,
                editor_font_family TEXT,
                editor_font_size INTEGER,
                target_word_count INTEGER DEFAULT 100000,
                category_order TEXT DEFAULT NULL,
                expanded_categories TEXT DEFAULT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE chapters (
                id TEXT PRIMARY KEY, parent_id TEXT, name TEXT, node_type TEXT,
                content TEXT, mark TEXT, sort_order INTEGER, scene_summary TEXT,
                scene_pov TEXT, scene_location TEXT, is_expanded INTEGER DEFAULT 1
            )
        ''')
        cursor.execute('''
            CREATE TABLE writing_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE, duration INTEGER, word_count INTEGER,
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
        cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (9, '2026-09-01 00:00:00')")
        cursor.execute("INSERT INTO project_info (title, target_word_count) VALUES ('v9舊檔', 80000)")
        conn.commit()
        conn.close()

        # 執行 Migration
        loaded = DatabaseService.load_project(self.db_path)
        self.assertEqual(loaded.project_info.title, "v9舊檔")
        self.assertEqual(loaded.project_info.daily_target_word_count, 1000)

        # 檢查 schema_version 是否已成功升級至最新版本 (>= 10)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(version) FROM schema_version")
        v = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(v, DatabaseService.CURRENT_SCHEMA_VERSION)

    def test_load_project_restores_today_target_and_progress(self):
        """驗證跨設備載入專案時，能自動還原當日目標與今日已寫字數進度。"""
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        project = JneProject()
        project.project_info = ProjectInfo(
            title="跨設備同步作品",
            daily_target_word_count=3000
        )
        # 模擬在設備 A 寫了 850 字
        project.writing_logs.append(WritingLogEntry(
            date=today_str,
            duration=1200,
            word_count=850
        ))
        DatabaseService.save_project(project, self.db_path)

        # 模擬設備 B 開啟軟體並載入專案
        self.mc.autosave.save_temp_doc = MagicMock()

        loaded = DatabaseService.load_project(self.db_path)
        self.mc.project.load_project_data(loaded)

        # 驗證目標與進度
        self.assertEqual(self.mc.today_target, 3000)
        self.assertEqual(self.mc.today_written_count, 850)
        self.assertEqual(self.view.progress_bar.maximum(), 3000)
        self.assertEqual(self.view.progress_bar.value(), 850)

    def test_load_project_different_date_resets_today_progress(self):
        """驗證若存檔中的寫作紀錄屬於過去日期，今日進度會歸零。"""
        project = JneProject()
        project.project_info = ProjectInfo(
            title="隔天開檔專案",
            daily_target_word_count=2000
        )
        # 模擬昨天的寫作紀錄
        project.writing_logs.append(WritingLogEntry(
            date="2020-01-01",
            duration=3600,
            word_count=1500
        ))
        DatabaseService.save_project(project, self.db_path)

        self.mc.autosave.save_temp_doc = MagicMock()

        loaded = DatabaseService.load_project(self.db_path)
        self.mc.project.load_project_data(loaded)

        self.assertEqual(self.mc.today_target, 2000)
        self.assertEqual(self.mc.today_written_count, 0)
        self.assertEqual(self.view.progress_bar.value(), 0)

    def test_set_daily_target_persists_and_saves(self):
        """驗證設定每日目標會同步更新 project_info 並觸發暫存。"""
        self.mc.save_temp_doc = MagicMock()

        with patch("PyQt6.QtWidgets.QInputDialog.getInt", return_value=(4500, True)):
            self.mc.stats.set_daily_target()

        self.assertEqual(self.mc.today_target, 4500)
        self.assertEqual(self.mc.project_info.daily_target_word_count, 4500)
        self.mc.save_temp_doc.assert_called_once()

    def test_clear_daily_progress_clears_today_log_and_saves(self):
        """驗證清除今日進度時，同步將 writing_logs 中當日字數清為 0 並觸發暫存。"""
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        self.mc.today_written_count = 500
        self.mc.writing_logs = [
            WritingLogEntry(date=today_str, duration=600, word_count=500)
        ]
        self.mc.save_temp_doc = MagicMock()

        with patch("PyQt6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            self.mc.stats.clear_daily_progress()

        self.assertEqual(self.mc.today_written_count, 0)
        self.assertEqual(self.mc.writing_logs[0].word_count, 0)
        self.mc.save_temp_doc.assert_called_once()

    def test_flush_writing_session_syncs_with_today_written_count(self):
        """驗證結束寫作 Session (flush) 時，當日日誌字數與 today_written_count 保持一致。"""
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        self.mc.today_written_count = 800
        self.mc.writing_logs = [
            WritingLogEntry(date=today_str, duration=300, word_count=600)
        ]

        now = datetime.datetime.now()
        start_str = (now - datetime.timedelta(seconds=120)).strftime("%Y-%m-%d %H:%M:%S")
        last_str = now.strftime("%Y-%m-%d %H:%M:%S")
        self.mc.active_session = {
            "start_time": start_str,
            "last_action_time": last_str,
            "words_added": 200
        }

        self.mc.stats.flush_active_writing_session()
        self.assertEqual(self.mc.writing_logs[0].word_count, 800)
        self.assertGreaterEqual(self.mc.writing_logs[0].duration, 420)


if __name__ == "__main__":
    unittest.main()
