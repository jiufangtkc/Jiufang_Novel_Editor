import os
import sys
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QTextCursor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from views.main_window import MainWindow
from controllers.main_controller import MainController


class TestTypewriterMode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

    def setUp(self):
        self.view = MainWindow()
        self.mc = MainController(self.view)
        self.view.show()
        self.app.processEvents()

    def tearDown(self):
        self.mc.writing_timer.stop()
        self.mc.auto_save_timer.stop()
        self.view.close()

    def test_toggle_typewriter(self):
        """測試打字機模式切換與按鈕文字狀態。"""
        self.assertFalse(self.mc.typewriter_mode)
        self.assertEqual(self.view.btn_typewriter.text(), "打字機模式: 關")

        self.mc.editor.toggle_typewriter(True)
        self.assertTrue(self.mc.typewriter_mode)
        self.assertEqual(self.view.btn_typewriter.text(), "打字機模式: 開")

        self.mc.editor.toggle_typewriter(False)
        self.assertFalse(self.mc.typewriter_mode)
        self.assertEqual(self.view.btn_typewriter.text(), "打字機模式: 關")

    def test_typewriter_cursor_movement_does_not_scroll(self):
        """測試游標移動（如滑鼠點擊或選取引起的 cursorPositionChanged）不會強行滾動視窗。"""
        long_text = "\n".join([f"這是小說測試第 {i} 行內容。" for i in range(1, 100)])
        self.view.editor.setPlainText(long_text)
        self.app.processEvents()

        self.mc.typewriter_mode = True
        scrollbar = self.view.editor.verticalScrollBar()
        scrollbar.setValue(300)
        self.app.processEvents()
        initial_val = scrollbar.value()

        # 在可見區域內移動游標並觸發 on_cursor_position_changed
        cursor = self.view.editor.cursorForPosition(self.view.editor.rect().center())
        self.view.editor.setTextCursor(cursor)
        scrollbar.setValue(initial_val)

        # 移動游標幾個字元，模擬在同畫面滑鼠點擊或鍵盤方向鍵移動
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, 3)
        self.view.editor.setTextCursor(cursor)
        self.mc.editor.on_cursor_position_changed()

        # 驗證滾動條維持原值，未被強制向中央位移
        self.assertEqual(scrollbar.value(), initial_val)

    def test_typewriter_no_align_when_has_selection(self):
        """測試當游標選取文字時（如滑鼠拖曳反白），嚴格禁止滾動對齊，防止畫面亂跳。"""
        long_text = "\n".join([f"小說段落 {i}。" for i in range(1, 80)])
        self.view.editor.setPlainText(long_text)
        self.app.processEvents()

        self.mc.typewriter_mode = True
        scrollbar = self.view.editor.verticalScrollBar()
        scrollbar.setValue(200)
        saved_val = scrollbar.value()

        # 選取一段文字 (hasSelection = True)
        cursor = self.view.editor.textCursor()
        cursor.setPosition(0)
        cursor.setPosition(200, QTextCursor.MoveMode.KeepAnchor)
        self.view.editor.setTextCursor(cursor)
        self.assertTrue(self.view.editor.textCursor().hasSelection())

        # 呼叫打字機中央對齊
        self.mc.editor.align_typewriter_center()

        # 驗證滾動條未變動
        self.assertEqual(scrollbar.value(), saved_val)

    def test_typewriter_align_on_typing(self):
        """測試打字機模式開啟下，文字變更（打字輸入）時能正確執行置中對齊。"""
        long_text = "\n".join([f"章節內容第 {i} 行。" for i in range(1, 100)])
        self.view.editor.setPlainText(long_text)
        self.app.processEvents()

        self.mc.typewriter_mode = True
        # 將游標移至中間某行並打字（插入文字）
        cursor = self.view.editor.textCursor()
        cursor.setPosition(len(long_text) // 2)
        self.view.editor.setTextCursor(cursor)

        cursor_rect = self.view.editor.cursorRect(cursor)
        viewport_height = self.view.editor.viewport().height()
        scrollbar = self.view.editor.verticalScrollBar()
        expected_target_y = max(0, int(cursor_rect.top() + scrollbar.value() - (viewport_height / 2)))

        self.mc.editor.align_typewriter_center()
        self.assertEqual(scrollbar.value(), expected_target_y)

    def test_typewriter_disabled_no_align(self):
        """測試打字機模式關閉時，align_typewriter_center 不會強制置中。"""
        self.mc.typewriter_mode = False
        scrollbar = self.view.editor.verticalScrollBar()
        scrollbar.setValue(50)
        initial_val = scrollbar.value()

        self.mc.editor.align_typewriter_center()
        self.assertEqual(scrollbar.value(), initial_val)
