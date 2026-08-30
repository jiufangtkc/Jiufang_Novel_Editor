import os
import sys
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from views.main_window import MainWindow
from controllers.main_controller import MainController

class TestSearch(unittest.TestCase):
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

    def test_search_controller_initialization(self):
        """驗證 SearchController 正確初始化並連接到 MainController。"""
        self.assertIsNotNone(self.mc.search)
        self.assertEqual(self.mc.search.mc, self.mc)
        self.assertIsNotNone(self.view.find_replace_bar)
        self.assertTrue(self.view.find_replace_bar.isHidden())

    def test_find_in_editor_and_navigation(self):
        """測試編輯器內關鍵字搜尋與前後導航。"""
        content = "九方小說編輯器是一款專為小說創作者設計的小說軟體。小說萬歲！"
        self.view.editor.setPlainText(content)

        # 搜尋「小說」
        self.mc.search.find_in_editor("小說", match_case=False, whole_word=False, is_regex=False)

        # 共有 4 處「小說」
        self.assertEqual(len(self.mc.search.current_matches), 4)
        self.assertEqual(self.mc.search.current_match_index, 0)

        # 測試跳至下一個
        self.mc.search.find_next()
        self.assertEqual(self.mc.search.current_match_index, 1)

        self.mc.search.find_next()
        self.assertEqual(self.mc.search.current_match_index, 2)

        # 測試跳至上一個
        self.mc.search.find_prev()
        self.assertEqual(self.mc.search.current_match_index, 1)

    def test_search_options(self):
        """測試搜尋選項：大小寫、全字比對、正規表達式。"""
        content = "Hero hero HERO heroine 123"
        self.view.editor.setPlainText(content)

        # 1. 區分大小寫
        self.mc.search.find_in_editor("Hero", match_case=True, whole_word=False, is_regex=False)
        self.assertEqual(len(self.mc.search.current_matches), 1)

        # 不區分大小寫
        self.mc.search.find_in_editor("Hero", match_case=False, whole_word=False, is_regex=False)
        self.assertEqual(len(self.mc.search.current_matches), 4)  # Hero, hero, HERO, heroine 中的 hero

        # 2. 全字相符
        self.mc.search.find_in_editor("hero", match_case=False, whole_word=True, is_regex=False)
        self.assertEqual(len(self.mc.search.current_matches), 3)  # Hero, hero, HERO（排除 heroine）

        # 3. 正規表達式
        self.mc.search.find_in_editor(r"\d+", match_case=False, whole_word=False, is_regex=True)
        self.assertEqual(len(self.mc.search.current_matches), 1)

    def test_single_replace_and_replace_all(self):
        """測試單次取代與全部取代。"""
        content = "貓咪一號，貓咪二號，貓咪三號"
        self.view.editor.setPlainText(content)

        # 尋找列設定
        self.view.find_replace_bar.input_find.setText("貓咪")
        self.view.find_replace_bar.input_replace.setText("小狗")
        self.mc.search.find_in_editor("貓咪")

        self.assertEqual(len(self.mc.search.current_matches), 3)

        # 單次取代（第 1 個）
        self.mc.search.replace()
        self.assertTrue(self.view.editor.toPlainText().startswith("小狗一號"))

        # 全部取代剩下項目
        self.mc.search.replace_all()
        self.assertEqual(self.view.editor.toPlainText(), "小狗一號，小狗二號，小狗三號")

    def test_global_search_across_chapters(self):
        """測試跨章節全文搜尋與結果摘要。"""
        # 清除並建立測試章節樹
        self.view.tree_widget.clear()

        item1 = self.mc.tree.create_item("第一章 啟程", is_folder=False, content="主角在雨夜中出發，帶著劍與行囊。")
        item2 = self.mc.tree.create_item("第二章 冒險", is_folder=False, content="主角遇見了一位神秘的老人，獲得了一把神劍。")
        item3 = self.mc.tree.create_item("第三章 歸途", is_folder=False, content="故事在此告一段落。")

        self.view.tree_widget.addTopLevelItem(item1)
        self.view.tree_widget.addTopLevelItem(item2)
        self.view.tree_widget.addTopLevelItem(item3)

        # 搜尋關鍵字「主角」
        pattern = self.mc.search._build_regex_pattern("主角", match_case=False, whole_word=False, is_regex=False)
        results = []
        for i in range(self.view.tree_widget.topLevelItemCount()):
            top = self.view.tree_widget.topLevelItem(i)
            self.mc.search._search_tree_item_recursive(top, pattern, results)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["chapter_path"], "第一章 啟程")
        self.assertEqual(results[1]["chapter_path"], "第二章 冒險")
        self.assertIn("主角", results[0]["snippet"])

        # 測試跳轉定位
        node_id_2 = self.mc.tree.get_item_id(item2)
        self.mc.search.navigate_to_global_match(node_id_2, line_num=1, char_offset=0, match_len=2)

        self.assertEqual(self.view.tree_widget.currentItem(), item2)
        self.assertEqual(self.view.editor.textCursor().selectedText(), "主角")

if __name__ == "__main__":
    unittest.main()
