import unittest
import tempfile
import os
import shutil
import sys
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from views.main_window import MainWindow
from controllers.main_controller import MainController
from models.models import CardNode, BUILTIN_CATEGORIES

app = QApplication.instance() or QApplication(sys.argv)

class TestRightPanelSplit(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.view = MainWindow()
        self.mc = MainController(self.view)
        self.mc.app_dir = self.temp_dir.name
        self.rp = self.view.right_panel

    def tearDown(self):
        self.view.close()
        self.temp_dir.cleanup()

    def test_initial_state_placeholder(self):
        """測試預設下方欄位顯示提示頁 (Index 0)。"""
        self.assertEqual(self.rp.bottom_stack.currentIndex(), 0)
        self.assertIsNone(self.rp.current_editing_card_id)

    def test_click_card_loads_content(self):
        """測試點選卡片節點時，下方欄位切換至編輯頁 (Index 1) 並正確載入標題與內文。"""
        card = CardNode(title="神劍設定", content="此劍擁有開天闢地之力。")
        self.mc.project_cards["world"] = [card]
        self.mc.card.rebuild_card_tree()

        card_item = self.mc.card._find_tree_item_by_id(card.id)
        self.assertIsNotNone(card_item)

        # 模擬點擊卡片節點
        self.rp._on_item_clicked(card_item, 0)

        self.assertEqual(self.rp.bottom_stack.currentIndex(), 1)
        self.assertEqual(self.rp.current_editing_card_id, card.id)
        self.assertEqual(self.rp.card_title_edit.text(), "神劍設定")
        self.assertEqual(self.rp.card_content_edit.toPlainText(), "此劍擁有開天闢地之力。")
        self.assertIn("世界觀", self.rp.lbl_card_category.text())

    def test_save_card_from_panel(self):
        """測試在下方欄位修改內容並點擊儲存，資料模型與樹狀節點皆正確更新。"""
        card = CardNode(title="舊標題", content="舊內容")
        self.mc.project_cards["character"] = [card]
        self.mc.card.rebuild_card_tree()

        card_item = self.mc.card._find_tree_item_by_id(card.id)
        self.rp._on_item_clicked(card_item, 0)

        # 修改下方欄位文字
        self.rp.card_title_edit.setText("主角設定（新）")
        self.rp.card_content_edit.setPlainText("性格堅毅，善於劍術。")

        # 點擊儲存按鈕
        self.rp.btn_save_card_content.click()

        # 驗證資料模型更新
        self.assertEqual(card.title, "主角設定（新）")
        self.assertEqual(card.content, "性格堅毅，善於劍術。")

        # 驗證樹狀節點顯示更新
        self.assertEqual(card_item.text(0).strip(), "主角設定（新）")

    def test_click_category_shows_placeholder(self):
        """測試點擊分類節點時切換回提示頁 (Index 0)。"""
        card = CardNode(title="卡片 A", content="內容 A")
        self.mc.project_cards["summary"] = [card]
        self.mc.card.rebuild_card_tree()

        card_item = self.mc.card._find_tree_item_by_id(card.id)
        self.rp._on_item_clicked(card_item, 0)
        self.assertEqual(self.rp.bottom_stack.currentIndex(), 1)

        # 點擊頂層分類節點
        cat_item = self.rp.card_tree.topLevelItem(0)
        self.rp._on_item_clicked(cat_item, 0)
        self.assertEqual(self.rp.bottom_stack.currentIndex(), 0)
        self.assertIsNone(self.rp.current_editing_card_id)

    def test_delete_editing_card_resets_to_placeholder(self):
        """測試當正在編輯的卡片被刪除時，下方欄位重設為提示頁。"""
        card = CardNode(title="即將被刪除", content="內容")
        self.mc.project_cards["summary"] = [card]
        self.mc.card.rebuild_card_tree()

        card_item = self.mc.card._find_tree_item_by_id(card.id)
        self.rp._on_item_clicked(card_item, 0)
        self.assertEqual(self.rp.bottom_stack.currentIndex(), 1)

        # 刪除卡片
        self.mc.card.delete_card(card.id, "summary")
        self.assertEqual(self.rp.bottom_stack.currentIndex(), 0)

    def test_scene_panel_switch(self):
        """測試切換幕屬性編輯面板 (Index 2)。"""
        self.rp.set_scene_panel_visible(True)
        self.assertEqual(self.rp.bottom_stack.currentIndex(), 2)

        self.rp.set_scene_panel_visible(False)
        self.assertEqual(self.rp.bottom_stack.currentIndex(), 0)

    def test_card_rename_sync_with_editing_panel(self):
        """測試當卡片更名時，下方正在開啟的編輯欄位標題即時連動更新。"""
        from unittest.mock import patch
        card = CardNode(title="原標題", content="內文測試")
        self.mc.project_cards["world"] = [card]
        self.mc.card.rebuild_card_tree()

        card_item = self.mc.card._find_tree_item_by_id(card.id)
        self.rp._on_item_clicked(card_item, 0)
        self.assertEqual(self.rp.card_title_edit.text(), "原標題")

        # 模擬呼叫 rename_card
        with patch("PyQt6.QtWidgets.QInputDialog.getText", return_value=("世界觀新標題", True)):
            self.mc.card.rename_card(card.id, "world")

        # 驗證下方欄位標題與卡片資料同步更新
        self.assertEqual(card.title, "世界觀新標題")
        self.assertEqual(self.rp.card_title_edit.text(), "世界觀新標題")

    def test_markdown_highlighter_and_formatting(self):
        """測試卡片編輯區掛載 MarkdownHighlighter，且工具列格式化按鈕正常運作。"""
        self.assertIsNotNone(getattr(self.rp.card_content_edit, "highlighter", None))
        
        # 測試文字包裹格式化 (Bold / Italic / Strike)
        self.rp.card_content_edit.setPlainText("測試文字")
        cursor = self.rp.card_content_edit.textCursor()
        cursor.select(cursor.SelectionType.Document)
        self.rp.card_content_edit.setTextCursor(cursor)
        
        self.rp.btn_format_bold.click()
        self.assertEqual(self.rp.card_content_edit.toPlainText(), "**測試文字**")
        
        # 再次點擊解除包裹
        cursor = self.rp.card_content_edit.textCursor()
        cursor.select(cursor.SelectionType.Document)
        self.rp.card_content_edit.setTextCursor(cursor)
        self.rp.btn_format_bold.click()
        self.assertEqual(self.rp.card_content_edit.toPlainText(), "測試文字")

    def test_markdown_preview_toggle(self):
        """測試卡片 Markdown 富文本預覽切換功能。"""
        self.rp.card_content_edit.setPlainText("### 標題\n**粗體內容**")
        self.assertEqual(self.rp.card_content_stack.currentIndex(), 0)
        
        # 點擊切換為預覽模式
        self.rp.btn_toggle_card_preview.click()
        self.assertEqual(self.rp.card_content_stack.currentIndex(), 1)
        self.assertEqual(self.rp.btn_toggle_card_preview.text(), "📝 編輯")
        self.assertIn("<h3", self.rp.card_preview_browser.toHtml())
        self.assertIn("font-weight:700", self.rp.card_preview_browser.toHtml())
        self.assertIn("標題", self.rp.card_preview_browser.toPlainText())
        self.assertIn("粗體內容", self.rp.card_preview_browser.toPlainText())
        self.assertFalse(self.rp.btn_format_bold.isEnabled())

        # 再次點擊切換回編輯模式
        self.rp.btn_toggle_card_preview.click()
        self.assertEqual(self.rp.card_content_stack.currentIndex(), 0)
        self.assertEqual(self.rp.btn_toggle_card_preview.text(), "📖 預覽")
        self.assertTrue(self.rp.btn_format_bold.isEnabled())

if __name__ == "__main__":
    unittest.main()

