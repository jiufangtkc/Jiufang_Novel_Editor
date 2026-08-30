import os
import sys
import tempfile
import unittest
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.models import JneProject, ProjectInfo
from services.database import DatabaseService
from views.main_window import MainWindow
from controllers.main_controller import MainController
from views.dialogs.word_count_settings_dialog import WordCountSettingsDialog


class TestStatsSettings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

    def setUp(self):
        self.view = MainWindow()
        self.mc = MainController(self.view)

    def tearDown(self):
        self.mc.writing_timer.stop()
        self.mc.auto_save_timer.stop()
        self.view.close()

    def test_word_count_rules_switching(self):
        """測試字數統計規則在不同開關組合下的計算結果。"""
        text = "這是一段測試 123 ABC !?　全形結束。"
        # 全形中文與全形標點：這是一段測試全形結束。 (11 字)
        # 半形英數符號：123(3) + ABC(3) + !?(2) = 8 字
        # 半形空格：3 個
        # 全形空格：1 個

        # 1. 預設模式（排除半形英數符號空格、排除全形空格）
        self.mc.app_settings["stat_count_half_alnum_and_sym"] = False
        self.mc.app_settings["stat_count_full_space"] = False
        stats = self.mc.stats.analyze_exclusions(text)
        self.assertEqual(stats["cjk"], 11)
        self.assertEqual(stats["half_alnum_sym"], 8)
        self.assertEqual(stats["half_spaces"], 3)
        self.assertEqual(stats["full_spaces"], 1)
        self.assertEqual(stats["valid"], 11)

        # 2. 啟用計算半形英數字、符號與半形空格
        self.mc.app_settings["stat_count_half_alnum_and_sym"] = True
        self.mc.app_settings["stat_count_full_space"] = False
        stats = self.mc.stats.analyze_exclusions(text)
        # 11 (cjk) + 8 (half) + 3 (half spaces) = 22
        self.assertEqual(stats["valid"], 22)

        # 3. 僅啟用計算全形空格
        self.mc.app_settings["stat_count_half_alnum_and_sym"] = False
        self.mc.app_settings["stat_count_full_space"] = True
        stats = self.mc.stats.analyze_exclusions(text)
        # 11 (cjk) + 1 (full space) = 12
        self.assertEqual(stats["valid"], 12)

        # 4. 同時啟用半形與全形空格
        self.mc.app_settings["stat_count_half_alnum_and_sym"] = True
        self.mc.app_settings["stat_count_full_space"] = True
        stats = self.mc.stats.analyze_exclusions(text)
        # 11 + 8 + 3 + 1 = 23
        self.assertEqual(stats["valid"], 23)

    def test_status_bar_detailed_tooltip(self):
        """測試狀態列詳細統計 ToolTip 的產生與規則標註。"""
        self.mc.app_settings["stat_count_half_alnum_and_sym"] = False
        self.mc.app_settings["stat_count_full_space"] = False
        self.view.editor.setPlainText("測試中文字 Hello 123　全形")
        self.mc.update_status_bar()

        tooltip = self.view.lbl_word_count.toolTip()
        self.assertIn("字數詳細統計", tooltip)
        self.assertIn("全形中文（含全形標點）", tooltip)
        self.assertIn("半形英數（含半形符號）", tooltip)
        self.assertIn("統計規則狀態", tooltip)
        self.assertIn("已排除", tooltip)
        self.assertIn("當前生效總字數", tooltip)

    def test_project_progress_bar_and_target(self):
        """測試寫作專案總進度條與目標設定。"""
        self.mc.project_info.target_word_count = 50000
        self.mc.file_word_stats["scene_1"] = {"valid": 10000, "cjk": 10000, "half_alnum_sym": 0, "half_spaces": 0, "full_spaces": 0}
        self.mc.update_status_bar()

        self.assertEqual(self.view.project_progress_bar.maximum(), 50000)
        self.assertEqual(self.view.project_progress_bar.value(), 10000)
        self.assertIn("專案總進度: 10000 / 50000 字 (20%)", self.view.lbl_project_progress.text())

    def test_database_schema_v6_target_word_count(self):
        """測試 SQLite 資料庫在 schema v6 下正確持久化 target_word_count。"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            db_path = tf.name

        try:
            proj = JneProject(
                project_info=ProjectInfo(
                    title="目標字數測試書",
                    logline="一本文學巨著",
                    target_word_count=200000
                )
            )
            DatabaseService.save_project(proj, db_path)

            loaded_proj = DatabaseService.load_project(db_path)
            self.assertEqual(loaded_proj.project_info.target_word_count, 200000)
            self.assertEqual(loaded_proj.project_info.title, "目標字數測試書")
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_word_count_settings_dialog(self):
        """測試 WordCountSettingsDialog 初始化與值讀取。"""
        dlg = WordCountSettingsDialog(None, count_half_alnum_and_sym=True, count_full_space=False)
        self.assertTrue(dlg.chk_half.isChecked())
        self.assertFalse(dlg.chk_full_space.isChecked())
        half_res, full_res = dlg.get_settings()
        self.assertTrue(half_res)
        self.assertFalse(full_res)
