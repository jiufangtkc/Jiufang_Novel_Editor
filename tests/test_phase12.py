import unittest
import os
import tempfile
import sqlite3
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from models.models import JneProject, ProjectInfo, ChapterNode, CardNode, WritingLogEntry
from services.database import DatabaseService
from services.lint_service import LintService, LintIssue
from views.main_window import MainWindow
from controllers.main_controller import MainController
from views.dialogs.lint_dialog import LintDialog
from views.dialogs.lint_whitelist_dialog import LintWhitelistDialog

class TestPhase12(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_phase12.db")
        self.lint_cfg_path = os.path.join(self.temp_dir.name, "test_lint_settings.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    # =========================================================================
    # 1. AI 介入度記錄與 SQLite 儲存/Migration 測試
    # =========================================================================
    def test_writing_log_entry_ai_fields(self):
        """驗證 WritingLogEntry 正確定義並初始化 AI 介入度欄位。"""
        log = WritingLogEntry(date="2026-08-25", duration=120, word_count=500)
        self.assertEqual(log.ai_continuation_count, 0)
        self.assertEqual(log.ai_continuation_chars, 0)
        self.assertEqual(log.ai_chat_count, 0)

        log.ai_continuation_count = 3
        log.ai_continuation_chars = 450
        log.ai_chat_count = 5
        self.assertEqual(log.ai_continuation_chars, 450)

    def test_database_writing_logs_migration_and_persistence(self):
        """驗證 SQLite writing_logs 自動 Migration 與 AI 介入度資料完整儲存與還原。"""
        # 先建立一個不含 AI 欄位的舊版 SQLite 表
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE writing_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                duration INTEGER,
                word_count INTEGER
            )
        ''')
        cursor.execute("INSERT INTO writing_logs (date, duration, word_count) VALUES ('2026-08-20', 300, 800)")
        conn.commit()
        conn.close()

        # 呼叫 init_db 觸發 Migration
        DatabaseService.init_db(self.db_path)

        # 檢驗欄位是否已被自動補齊
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('PRAGMA table_info(writing_logs)')
        cols = {row[1] for row in cursor.fetchall()}
        self.assertIn("ai_continuation_count", cols)
        self.assertIn("ai_continuation_chars", cols)
        self.assertIn("ai_chat_count", cols)
        conn.close()

        # 測試存入含 AI 數據的專案
        project = JneProject()
        project.writing_logs = [
            WritingLogEntry(
                date="2026-08-25",
                duration=600,
                word_count=1200,
                ai_continuation_count=2,
                ai_continuation_chars=350,
                ai_chat_count=4
            )
        ]
        DatabaseService.save_project(project, self.db_path)

        # 重新讀取
        loaded = DatabaseService.load_project(self.db_path)
        self.assertEqual(len(loaded.writing_logs), 2)  # 含舊筆資料與新筆資料
        new_log = next(l for l in loaded.writing_logs if l.date == "2026-08-25")
        self.assertEqual(new_log.word_count, 1200)
        self.assertEqual(new_log.ai_continuation_count, 2)
        self.assertEqual(new_log.ai_continuation_chars, 350)
        self.assertEqual(new_log.ai_chat_count, 4)

    def test_stats_controller_record_ai_activity(self):
        """驗證 StatsController.record_ai_activity 正確累計當日 AI 統計數據。"""
        win = MainWindow()
        mc = MainController(win)

        initial_logs_count = len(mc.writing_logs)
        mc.stats.record_ai_activity(continuation_count=1, continuation_chars=180, chat_count=2)

        today_log = mc.writing_logs[-1]
        self.assertGreaterEqual(today_log.ai_continuation_count, 1)
        self.assertGreaterEqual(today_log.ai_continuation_chars, 180)
        self.assertGreaterEqual(today_log.ai_chat_count, 2)

        # 再次累加
        mc.stats.record_ai_activity(continuation_count=1, continuation_chars=120, chat_count=1)
        self.assertGreaterEqual(today_log.ai_continuation_count, 2)
        self.assertGreaterEqual(today_log.ai_continuation_chars, 300)
        self.assertGreaterEqual(today_log.ai_chat_count, 3)

        # 驗證 get_writing_logs_as_dict
        logs_dict = mc.get_writing_logs_as_dict()
        self.assertIn("ai_continuation_chars", logs_dict[-1])
        self.assertIn("ai_chat_count", logs_dict[-1])

    # =========================================================================
    # 2. 繁體中文贅詞與文風檢查引擎 (LintService) 測試
    # =========================================================================
    def test_lint_redundant_phrase_detection(self):
        """驗證公文與冗贅片語檢查規則。"""
        sample_text = "他針對這件事情進行了一個調查的動作，基本上來說是不可否認的是事實。"
        issues = LintService.check_text(sample_text)
        issue_types = [i.issue_type for i in issues]
        self.assertIn("redundant_phrase", issue_types)

        # 找到「進行了一個」
        target_texts = [i.target_text for i in issues]
        self.assertTrue(any("進行了一個" in t for t in target_texts))

    def test_lint_passive_voice_detection(self):
        """驗證被動語態弱句偵測。"""
        sample_text = "主角被黑衣人打倒在地上，隨後受到了嚴厲的懲罰。"
        issues = LintService.check_text(sample_text)
        issue_types = [i.issue_type for i in issues]
        self.assertIn("passive_voice", issue_types)

    def test_lint_high_density_particle(self):
        """驗證單句高頻虛詞密度偵測。"""
        sample_text = "他走進了房間了之後看了看桌子上的信件了，然後笑了。"
        issues = LintService.check_text(sample_text)
        issue_types = [i.issue_type for i in issues]
        self.assertIn("high_density_particle", issue_types)

    def test_lint_duplicate_words(self):
        """驗證相鄰重複中文詞彙偵測。"""
        sample_text = "他凝視著那把鋒利的長劍，那把鋒利的長劍在月光下閃耀。"
        issues = LintService.check_text(sample_text)
        issue_types = [i.issue_type for i in issues]
        self.assertIn("duplicate_words", issue_types)
        dup_targets = [i.target_text for i in issues if i.issue_type == "duplicate_words"]
        self.assertTrue(any("長劍" in t or "鋒利" in t for t in dup_targets))

    def test_lint_whitelist_and_custom_words(self):
        """驗證白名單能排除特定詞彙，自訂贅詞能被成功偵測。"""
        settings = LintService.get_default_settings()
        settings["whitelist"] = ["基本上", "長劍"]
        settings["custom_redundant_words"] = ["話說回來"]

        sample_text = "基本上長劍在月光下閃爍。話說回來，天色已晚。"
        issues = LintService.check_text(sample_text, settings)

        target_texts = [i.target_text for i in issues]
        # 白名單詞彙不應出現
        self.assertNotIn("基本上", target_texts)
        # 自訂贅詞應被偵測
        self.assertIn("話說回來", target_texts)

    def test_lint_master_toggle_and_rule_switches(self):
        """驗證總開關關閉或個別規則關閉時的行為。"""
        sample_text = "他進行了一個動作，被敵人擊倒了。"
        
        # 總開關關閉
        settings = LintService.get_default_settings()
        settings["enabled"] = False
        issues = LintService.check_text(sample_text, settings)
        self.assertEqual(len(issues), 0)

        # 僅開啟被動語態
        settings["enabled"] = True
        settings["rules"]["redundant_phrase"] = False
        settings["rules"]["passive_voice"] = True
        issues = LintService.check_text(sample_text, settings)
        issue_types = {i.issue_type for i in issues}
        self.assertNotIn("redundant_phrase", issue_types)
        self.assertIn("passive_voice", issue_types)

    # =========================================================================
    # 3. UI 與 Dialog 互動測試
    # =========================================================================
    def test_lint_dialog_lifecycle_and_navigation(self):
        """驗證 LintDialog 初始化、重新掃描與跳轉信號發送。"""
        win = MainWindow()
        win.editor.setPlainText("主角被壞人擊敗，基本上來說難以置信。")

        dlg = LintDialog(win, get_text_func=lambda: win.editor.toPlainText())
        self.assertGreater(dlg.table.rowCount(), 0)

        # 模擬點擊第一行發射跳轉信號
        navigated = []
        dlg.signal_navigate_to_text.connect(lambda s, e: navigated.append((s, e)))

        first_item = dlg.table.item(0, 0)
        dlg.on_table_item_clicked(first_item)
        self.assertTrue(len(navigated) > 0)
        dlg.close()

    def test_lint_whitelist_dialog_add_delete(self):
        """驗證白名單維護介面的新增與刪除操作。"""
        win = MainWindow()
        settings = LintService.get_default_settings()
        dlg = LintWhitelistDialog(win, settings)

        # 新增白名單詞彙
        dlg.input_whitelist.setText("我的專有名詞")
        dlg.add_whitelist_word()
        items = [dlg.list_whitelist.item(i).text() for i in range(dlg.list_whitelist.count())]
        self.assertIn("我的專有名詞", items)

        # 刪除白名單詞彙
        dlg.list_whitelist.setCurrentRow(dlg.list_whitelist.count() - 1)
        dlg.delete_whitelist_word()
        items_after = [dlg.list_whitelist.item(i).text() for i in range(dlg.list_whitelist.count())]
        self.assertNotIn("我的專有名詞", items_after)
        dlg.close()

    def test_writing_log_dashboard_and_chart_view(self):
        """驗證 WritingLogDashboard 指標計算與視圖模式切換。"""
        win = MainWindow()
        mc = MainController(win)
        dashboard = win.writing_log_dashboard

        # 填入假日誌數據
        test_logs = [
            {"date": "2026-08-24", "duration": 1800, "word_count": 800, "ai_continuation_chars": 200, "ai_chat_count": 3},
            {"date": "2026-08-25", "duration": 3600, "word_count": 1500, "ai_continuation_chars": 500, "ai_chat_count": 5}
        ]
        dashboard.refresh_data(test_logs)

        # 驗證指標卡片
        self.assertIn("1 小時 30 分", dashboard.card_duration.lbl_val.text())
        self.assertIn("2,300", dashboard.card_total_words.lbl_val.text())
        self.assertIn("700", dashboard.card_ai_ratio.lbl_val.text())

        # 驗證圖表視圖切換
        dashboard.btn_mode_heatmap.click()
        self.assertEqual(dashboard.chart_view.mode, "heatmap")
        dashboard.btn_mode_chapters.click()
        self.assertEqual(dashboard.chart_view.mode, "chapters")
        dashboard.btn_mode_ai.click()
        self.assertEqual(dashboard.chart_view.mode, "ai_ratio")
        dashboard.btn_mode_trend.click()
        self.assertEqual(dashboard.chart_view.mode, "trend")

if __name__ == "__main__":
    unittest.main()
