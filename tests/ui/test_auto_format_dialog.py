import os
import sys
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from views.main_window import MainWindow
from controllers.main_controller import MainController
from views.dialogs.auto_format_dialog import AutoFormatDialog
from services.text_formatter_service import TextFormatterService


class TestAutoFormatAndToolbar(unittest.TestCase):
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

    def test_auto_format_dialog_options_and_preview(self):
        """測試 AutoFormatDialog 選項取得與預覽連動。"""
        sample_text = "你好,世界.這是第一段。\n\n\n這是第二段~"
        dlg = AutoFormatDialog(self.view, current_text=sample_text)

        # 預設選項檢查
        opts = dlg.get_options()
        self.assertTrue(opts["convert_punctuation"])
        self.assertEqual(opts["indent_mode"], "indent")
        self.assertEqual(opts["empty_line_mode"], "compact")
        self.assertEqual(opts["scope"], "current")

        # 檢查預覽內容是否正確格式化
        preview_text = dlg.txt_preview.toPlainText()
        self.assertIn("\u3000\u3000你好，世界。這是第一段。", preview_text)
        self.assertIn("\u3000\u3000這是第二段～", preview_text)

        # 模擬切換為清除段首空格
        dlg.radio_indent_remove.setChecked(True)
        opts_removed = dlg.get_options()
        self.assertEqual(opts_removed["indent_mode"], "remove")
        preview_removed = dlg.txt_preview.toPlainText()
        self.assertTrue(preview_removed.startswith("你好，世界。"))

        dlg.close()

    def test_punctuation_toolbar_quote_wrapping(self):
        """測試常用標點工具列之引號包裹與插入居中功能。"""
        self.view.editor.setPlainText("你好世界")

        # 1. 有文字選取時點擊「」：包裹選取文字
        cursor = self.view.editor.textCursor()
        cursor.setPosition(0)
        cursor.setPosition(4, cursor.MoveMode.KeepAnchor)
        self.view.editor.setTextCursor(cursor)
        self.view.btn_punc_quote_single.click()

        self.assertEqual(self.view.editor.toPlainText(), "「你好世界」")

        # 2. 無文字選取時點擊『』：插入成對括號並將游標置中
        cursor = self.view.editor.textCursor()
        cursor.clearSelection()
        cursor.setPosition(6)  # 定位在最後
        self.view.editor.setTextCursor(cursor)
        self.view.btn_punc_quote_double.click()

        self.assertEqual(self.view.editor.toPlainText(), "「你好世界」『』")
        # 游標位置應位於 『 與 』 之間 (index 7)
        self.assertEqual(self.view.editor.textCursor().position(), 7)

    def test_punctuation_toolbar_single_punctuation_insert(self):
        """測試全形標點符號單一插入功能。"""
        self.view.editor.setPlainText("測試")
        cursor = self.view.editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.view.editor.setTextCursor(cursor)

        self.view.btn_punc_exclamation.click()
        self.view.btn_punc_question.click()
        self.view.btn_punc_colon.click()
        self.view.btn_punc_semicolon.click()
        self.view.btn_punc_comma_pause.click()
        self.view.btn_punc_section.click()

        self.assertEqual(self.view.editor.toPlainText(), "測試！？：；、※")

    def test_style_buttons_toggle(self):
        """測試粗體、斜體、刪除線按鈕切換與格式生效。"""
        self.view.editor.setPlainText("精彩小說")
        cursor = self.view.editor.textCursor()
        cursor.select(cursor.SelectionType.Document)
        self.view.editor.setTextCursor(cursor)

        # 粗體切換
        self.view.btn_bold.click()
        fmt = self.view.editor.textCursor().charFormat()
        self.assertTrue(fmt.fontWeight() >= 700)

        # 斜體切換
        self.view.btn_italic.click()
        fmt = self.view.editor.textCursor().charFormat()
        self.assertTrue(fmt.fontItalic())

        # 刪除線切換
        self.view.btn_strike.click()
        fmt = self.view.editor.textCursor().charFormat()
        self.assertTrue(fmt.fontStrikeOut())


if __name__ == "__main__":
    unittest.main()
