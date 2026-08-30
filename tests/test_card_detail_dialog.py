import sys
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QMimeData
from views.dialogs.card_detail_dialog import CardDetailDialog, CardDetailTextEdit


class TestCardDetailDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_plain_text_editing_and_data(self):
        """測試卡片詳情視窗純文字編輯與資料取得"""
        initial_text = "角色設定：主角具備冷靜沉著的性格與精湛的劍術。"
        dlg = CardDetailDialog(
            parent=None,
            title="主角設定",
            content=initial_text,
            color_hex="#336699",
            category_name="登場角色"
        )

        # 驗證純文字編輯器內容
        self.assertEqual(dlg.editor.toPlainText(), initial_text)
        self.assertFalse(dlg.editor.acceptRichText())

        # 編輯內文
        dlg.editor.setPlainText(initial_text + "\n附加背景故事。")
        data = dlg.get_data()
        self.assertEqual(data["title"], "主角設定")
        self.assertEqual(data["content"], initial_text + "\n附加背景故事。")
        self.assertEqual(data["color_hex"], "#336699")

        dlg.close()

    def test_plain_text_paste_strips_formatting(self):
        """測試無格式貼上功能：貼上 HTML / 富文本時自動過濾為純文字"""
        dlg = CardDetailDialog(parent=None, title="貼上測試", content="")
        
        mime = QMimeData()
        mime.setHtml("<b>粗體</b><i>斜體</i><span style='color:red;'>彩色文字</span>")
        mime.setText("粗體斜體彩色文字")
        
        dlg.editor.insertFromMimeData(mime)
        self.assertEqual(dlg.editor.toPlainText(), "粗體斜體彩色文字")
        self.assertNotIn("<b>", dlg.editor.toPlainText())
        self.assertNotIn("color:red", dlg.editor.toPlainText())

        dlg.close()


if __name__ == "__main__":
    unittest.main()
