import os
import sys
import unittest
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.models import JneProject, ProjectInfo, ChapterNode, CardNode, WritingLogEntry
from views.main_window import MainWindow
from controllers.main_controller import MainController

class TestControllers(unittest.TestCase):
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

    def test_subcontrollers_initialization(self):
        """驗證 9 個子控制器均正確實體化且共享 MainController。"""
        self.assertIsNotNone(self.mc.tree)
        self.assertIsNotNone(self.mc.editor)
        self.assertIsNotNone(self.mc.stats)
        self.assertIsNotNone(self.mc.project)
        self.assertIsNotNone(self.mc.autosave)
        self.assertIsNotNone(self.mc.theme)
        self.assertIsNotNone(self.mc.card)
        self.assertIsNotNone(self.mc.export_controller)
        self.assertIsNotNone(self.mc.ai_controller)
        self.assertIsNotNone(self.mc.search)

        self.assertEqual(self.mc.tree.mc, self.mc)
        self.assertEqual(self.mc.editor.mc, self.mc)
        self.assertEqual(self.mc.stats.mc, self.mc)
        self.assertEqual(self.mc.project.mc, self.mc)
        self.assertEqual(self.mc.autosave.mc, self.mc)
        self.assertEqual(self.mc.theme.mc, self.mc)
        self.assertEqual(self.mc.card.mc, self.mc)
        self.assertEqual(self.mc.search.mc, self.mc)

    def test_stats_controller_word_count_and_exclusions(self):
        """測試 StatsController 字數統計與排除分析。"""
        self.mc.app_settings["stat_count_half_alnum_and_sym"] = False
        self.mc.app_settings["stat_count_full_space"] = False
        text = "這是第一章 123 ABC !?　測試"
        # 中文字：這是第一章測試 (7 字)
        # 空格：4 個（含全形空格與半形空格）
        # 英數：123 ABC (6 個)
        # 符號：!? (2 個)
        stats = self.mc.stats.analyze_exclusions(text)
        self.assertEqual(stats["valid"], 7)
        self.assertEqual(stats["spaces"], 4)
        self.assertEqual(stats["alpha"], 6)
        self.assertEqual(stats["sym"], 2)

    def test_stats_controller_markdown_exclusions(self):
        """測試 Markdown 轉純文字後的排除統計。"""
        md_text = "# 第一章\n\n這是**粗體文字**與*斜體*。"
        stats = self.mc.stats.analyze_exclusions_from_markdown(md_text)
        self.assertGreater(stats["valid"], 0)

    def test_tree_controller_create_and_query_item(self):
        """測試 TreeController 節點建立與查詢。"""
        folder_item = self.mc.tree.create_item("第一卷", is_folder=True)
        file_item = self.mc.tree.create_item("第一回", is_folder=False, content="內文內容")

        self.assertTrue(self.mc.tree.is_item_valid(folder_item))
        self.assertTrue(self.mc.tree.is_item_valid(file_item))

        folder_id = self.mc.tree.get_item_id(folder_item)
        file_id = self.mc.tree.get_item_id(file_item)
        self.assertIsNotNone(folder_id)
        self.assertIsNotNone(file_id)

    def test_theme_controller_apply_theme(self):
        """測試 ThemeController 主題切換。"""
        self.mc.theme.apply_theme("celadon")
        self.assertEqual(self.view.current_theme, "celadon")
        self.assertEqual(self.view.folder_icon_color, "#7ea4b3")

        self.mc.theme.apply_theme("forest")
        self.assertEqual(self.view.current_theme, "forest")
        self.assertEqual(self.view.folder_icon_color, "#7aa89f")

    def test_card_controller_serialization(self):
        """測試 CardController 卡片序列化。"""
        from unittest.mock import patch
        with patch.object(self.mc.card, '_open_card_detail'):
            self.mc.card.add_core_card("character")
        cards = self.mc.card.serialize_all_cards()
        self.assertIn("character", cards)
        self.assertGreaterEqual(len(cards["character"]), 1)

    def test_project_controller_build_and_load(self):
        """測試 ProjectController dataclass 建立與載入。"""
        self.mc.project_info.title = "新書名"
        self.mc.project_info.logline = "大綱內容"
        project = self.mc.project._build_jne_project()

        self.assertEqual(project.project_info.title, "新書名")
        self.assertEqual(project.project_info.logline, "大綱內容")

        # 測試載入
        self.mc.project.load_project_data(project)
        self.assertEqual(self.mc.project_info.title, "新書名")
        self.assertEqual(self.mc.project_info.logline, "大綱內容")

    def test_main_editor_plain_text_paste_and_preservation(self):
        """測試主編輯器無格式貼上與純文字換行保留。"""
        from PyQt6.QtCore import QMimeData

        self.assertTrue(self.view.editor.acceptRichText())

        # 模擬貼上帶有 HTML / 富文本格式的剪貼簿資料
        mime = QMimeData()
        mime.setHtml("<h1>標題</h1><p style='color:red;'>第一段<b>粗體</b></p><br><p>第二段</p>")
        mime.setText("標題\n第一段粗體\n\n第二段")

        self.view.editor.clear()
        self.view.editor.insertFromMimeData(mime)
        pasted_text = self.view.editor.toPlainText().strip()

        self.assertEqual(pasted_text, "標題\n第一段粗體\n\n第二段")
        self.assertNotIn("<h1>", pasted_text)
        self.assertNotIn("style='color:red;'", pasted_text)
        self.assertNotIn("<b>", pasted_text)

    def test_trash_permanent_delete_and_clear(self):
        """測試垃圾桶永久刪除選取項目與清空垃圾桶功能。"""
        from unittest.mock import patch
        from PyQt6.QtWidgets import QMessageBox

        # 模擬建立垃圾桶項目
        item1 = self.mc.tree.create_item("廢棄章節1", is_folder=False, content="內容1")
        item2 = self.mc.tree.create_item("廢棄章節2", is_folder=False, content="內容2")

        self.mc.trash_bin.append({
            "item": item1, "parent": None, "index": 0, "name": "廢棄章節1", "path": "根目錄", "type": "file"
        })
        self.mc.trash_bin.append({
            "item": item2, "parent": None, "index": 1, "name": "廢棄章節2", "path": "根目錄", "type": "file"
        })
        self.mc.tree.refresh_trash_ui()
        self.assertEqual(self.view.trash_list_widget.count(), 2)

        # 測試永久刪除選取項目（第 0 列）
        self.view.trash_list_widget.setCurrentRow(0)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes), \
             patch.object(QMessageBox, 'information'):
            self.mc.tree.delete_selected_trash_item_permanently()

        self.assertEqual(len(self.mc.trash_bin), 1)
        self.assertEqual(self.mc.trash_bin[0]["name"], "廢棄章節2")
        self.assertEqual(self.view.trash_list_widget.count(), 1)

        # 測試清空垃圾桶
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes), \
             patch.object(QMessageBox, 'information'):
            self.mc.tree.clear_all_trash()

        self.assertEqual(len(self.mc.trash_bin), 0)
        self.assertEqual(self.view.trash_list_widget.count(), 0)

    def test_auto_load_latest_temp_priority_and_fallback(self):
        """測試啟動時自動檢查並優先載入最新時間戳記暫存檔與錯誤容錯。"""
        import tempfile
        import shutil
        from services.database import DatabaseService

        temp_workspace = tempfile.mkdtemp()
        try:
            temp_doc_dir = os.path.join(temp_workspace, "Temp_doc")
            os.makedirs(temp_doc_dir, exist_ok=True)

            # 建立舊暫存檔 (2026-08-20)
            old_project = JneProject(
                project_info=ProjectInfo(title="舊小說草稿", logline="舊大綱"),
                current_theme="default"
            )
            old_file = os.path.join(temp_doc_dir, "temp_20260820_100000.db")
            DatabaseService.save_project(old_project, old_file)

            # 建立新暫存檔 (2026-08-24)
            new_project = JneProject(
                project_info=ProjectInfo(title="最新小說定稿", logline="最新大綱"),
                current_theme="forest"
            )
            new_file = os.path.join(temp_doc_dir, "temp_20260824_150000.db")
            DatabaseService.save_project(new_project, new_file)

            # 暫時將 mc.app_dir 指向 temp_workspace 進行測試，並清空 storage_path 避免受全域設定干擾
            original_app_dir = self.mc.app_dir
            original_storage_path = self.mc.app_settings.get("storage_path")
            self.mc.app_dir = temp_workspace
            self.mc.app_settings["storage_path"] = ""
            try:
                loaded = self.mc.project.auto_load_latest_temp()
                self.assertTrue(loaded)
                self.assertEqual(self.mc.project_info.title, "最新小說定稿")
                self.assertEqual(self.mc.project_info.logline, "最新大綱")

                # 建立一個更晚的 0-byte 損毀暫存檔，測試容錯降級讀取
                corrupt_file = os.path.join(temp_doc_dir, "temp_20260824_180000.db")
                with open(corrupt_file, "w") as f:
                    f.write("")

                loaded_fallback = self.mc.project.auto_load_latest_temp()
                self.assertTrue(loaded_fallback)
                self.assertEqual(self.mc.project_info.title, "最新小說定稿")
            finally:
                self.mc.app_dir = original_app_dir
                if original_storage_path is not None:
                    self.mc.app_settings["storage_path"] = original_storage_path
                else:
                    self.mc.app_settings.pop("storage_path", None)
        finally:
            shutil.rmtree(temp_workspace, ignore_errors=True)

    def test_volume_and_book_title_independence(self):
        """測試書名與資料夾（卷）名稱彼此獨立，互不干涉。"""
        self.mc.project.init_default_project()
        self.mc.project_info.title = "我的長篇小說"
        self.mc.project.update_project_labels()
        self.assertEqual(self.view.lbl_project_title.text(), "我的長篇小說")

        # 頂層節點預設為「第一卷」
        top_item = self.view.tree_widget.topLevelItem(0)
        self.assertEqual(top_item.text(0), "第一卷")

        # 將第一卷改名為「第一卷：前妻與牛肉麵的香氣」
        top_item.setText(0, "第一卷：前妻與牛肉麵的香氣")
        self.mc.tree.on_tree_item_changed(top_item, 0)

        # 驗證書名未被修改
        self.assertEqual(self.mc.project_info.title, "我的長篇小說")
        self.assertEqual(self.view.lbl_project_title.text(), "我的長篇小說")

        # 驗證序列化儲存時，卷名與書名皆各自保留
        project = self.mc.project._build_jne_project()
        self.assertEqual(project.project_info.title, "我的長篇小說")
        self.assertEqual(project.tree[0].name, "第一卷：前妻與牛肉麵的香氣")

        # 驗證反序列化載入後，卷名與書名依然各自獨立
        self.mc.project.load_project_data(project)
        self.assertEqual(self.mc.project_info.title, "我的長篇小說")
        self.assertEqual(self.view.tree_widget.topLevelItem(0).text(0), "第一卷：前妻與牛肉麵的香氣")

    def test_theme_menu_scaling(self):
        """測試 ThemeManager 的 scale_qss 與選單 QSS 縮放。"""
        from utils.theme_manager import ThemeManager
        base_qss = ThemeManager.get_theme_qss("default")
        self.assertIn("QMenu::item", base_qss)
        self.assertIn("padding: 6px 36px 6px 24px;", base_qss)

        scaled_15 = ThemeManager.scale_qss(base_qss, 1.5)
        self.assertIn("padding: 9px 54px 9px 36px;", scaled_15)

        scaled_20 = ThemeManager.scale_qss(base_qss, 2.0)
        self.assertIn("padding: 12px 72px 12px 48px;", scaled_20)

    def test_writing_log_ai_fields_roundtrip(self):
        """驗證 _build_jne_project 與 load_project_data 完整保留 AI 介入度欄位 (B1/B2 防禦)。"""
        self.mc.project.init_default_project()
        self.mc.writing_logs = [
            WritingLogEntry(
                date="2026-08-30",
                duration=3600,
                word_count=2000,
                ai_continuation_count=5,
                ai_continuation_chars=650,
                ai_chat_count=3
            )
        ]

        # 序列化
        project = self.mc.project._build_jne_project()
        self.assertEqual(len(project.writing_logs), 1)
        log = project.writing_logs[0]
        self.assertEqual(log.ai_continuation_count, 5)
        self.assertEqual(log.ai_continuation_chars, 650)
        self.assertEqual(log.ai_chat_count, 3)

        # 反序列化
        self.mc.writing_logs = []
        self.mc.project.load_project_data(project)
        self.assertEqual(len(self.mc.writing_logs), 1)
        loaded_log = self.mc.writing_logs[0]
        self.assertEqual(loaded_log.ai_continuation_count, 5)
        self.assertEqual(loaded_log.ai_continuation_chars, 650)
        self.assertEqual(loaded_log.ai_chat_count, 3)

    def test_mark_color_map_consistency(self):
        """驗證 MARK_COLOR_MAP 包含完整的五種標記狀態且色碼正確 (D1 防禦)。"""
        from models.models import MARK_COLOR_MAP
        expected_keys = {"Draft", "1st Edit", "2nd Edit", "Final", "Discarded"}
        self.assertEqual(set(MARK_COLOR_MAP.keys()), expected_keys)
        self.assertEqual(MARK_COLOR_MAP["Draft"], "#808080")
        self.assertEqual(MARK_COLOR_MAP["1st Edit"], "#0000FF")
        self.assertEqual(MARK_COLOR_MAP["2nd Edit"], "#FFFF00")
        self.assertEqual(MARK_COLOR_MAP["Final"], "#008000")
        self.assertEqual(MARK_COLOR_MAP["Discarded"], "#FF0000")

if __name__ == "__main__":
    unittest.main()



