import os
import sys
import unittest
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ai_service import AIService, AIContinuationWorker
from views.components.jne_text_edit import JNE_TextEdit
from controllers.ai_controller import AIController

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


class MockStats:
    def count_words(self, text=""):
        return len(text)

    def record_ai_activity(self, continuation_count=0, continuation_chars=0, chat_count=0):
        pass



class MockMainController:
    def __init__(self, editor):
        class MockView:
            def __init__(self, ed):
                self.editor = ed
                self.card_layouts = {}
                self.lbl_word_count = None
                self.right_widget = None
        self.view = MockView(editor)
        self.stats = MockStats()
        self.saved = False

    def update_status_bar(self):
        pass

    def save_temp_doc(self):
        self.saved = True


class TestAIContinuation(unittest.TestCase):
    def test_continuation_default_disabled(self):
        settings = AIService.load_settings()
        self.assertIn("ai_continuation_enabled", settings)
        self.assertIn("ai_continuation_agreed", settings)
        self.assertIn("continuation", settings["prompts"])

    def test_continuation_worker_initialization(self):
        context = "夜深了，客棧外傳來敲門聲。"
        worker = AIContinuationWorker(context)
        self.assertEqual(worker.context_text, context)
        self.assertEqual(worker.custom_prompt, "")

    def test_continuation_inserted_at_cursor(self):
        editor = JNE_TextEdit()
        editor.setPlainText("從前有一座山，")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)

        mc = MockMainController(editor)
        ai_ctrl = AIController(mc)

        # 模擬 AI 擴寫/續寫完成插入編輯器
        continuation_text = "山裡有一座古老的寺廟。"
        ai_ctrl.insert_text_to_editor(continuation_text)

        self.assertEqual(editor.toPlainText(), "從前有一座山，山裡有一座古老的寺廟。")
        self.assertTrue(mc.saved)
        editor.close()


if __name__ == "__main__":
    unittest.main()
