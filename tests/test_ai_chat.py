import os
import sys
import unittest
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from views.dialogs.ai_chat_dialog import AIChatDialog

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


class TestAIChatDialog(unittest.TestCase):
    def setUp(self):
        self.dialog = AIChatDialog(initial_context="主角手持長劍，站在崖邊。")

    def tearDown(self):
        if hasattr(self.dialog, 'worker') and self.dialog.worker and self.dialog.worker.isRunning():
            self.dialog.worker.terminate()
            self.dialog.worker.wait(500)
        self.dialog.close()

    def test_init_with_context(self):
        self.assertEqual(self.dialog.initial_context, "主角手持長劍，站在崖邊。")
        self.assertIsNotNone(self.dialog.chk_include_context)
        self.assertTrue(self.dialog.chk_include_context.isChecked())
        self.assertIn("主角手持長劍", self.dialog.lbl_context_preview.text())

    def test_init_without_context(self):
        dlg_no_ctx = AIChatDialog(initial_context="")
        self.assertIsNone(dlg_no_ctx.chk_include_context)
        dlg_no_ctx.close()

    def test_message_formatting_and_history(self):
        # 模擬使用者送出訊息（mock worker.start 避免產生真實網路請求線程）
        from unittest.mock import patch
        with patch('views.dialogs.ai_chat_dialog.AIChatWorker.start'):
            self.dialog.input_edit.setPlainText("這段描寫可以如何加強氣氛？")
            self.dialog._on_send_clicked()

        # 檢查 messages 是否包含上下文與問題

        self.assertEqual(len(self.dialog.messages), 1)
        self.assertEqual(self.dialog.messages[0]["role"], "user")
        self.assertIn("【參考上下文】", self.dialog.messages[0]["content"])
        self.assertIn("主角手持長劍", self.dialog.messages[0]["content"])
        self.assertIn("這段描寫可以如何加強氣氛？", self.dialog.messages[0]["content"])

        # 模擬 Worker 回應
        reply = "可以加入風聲與雷鳴的環境渲染，例如：『狂風呼嘯，崖底傳來隱約的雷鳴』。"
        self.dialog._on_worker_finished(reply)

        self.assertEqual(len(self.dialog.messages), 2)
        self.assertEqual(self.dialog.messages[1]["role"], "assistant")
        self.assertEqual(self.dialog.messages[1]["content"], reply)
        self.assertEqual(self.dialog.last_assistant_reply, reply)
        self.assertTrue(self.dialog.btn_copy.isEnabled())
        self.assertTrue(self.dialog.btn_insert.isEnabled())
        self.assertTrue(self.dialog.btn_save_card.isEnabled())

    def test_insert_and_save_card_signals(self):
        received_insert = []
        received_card = []

        self.dialog.signal_insert_to_editor.connect(lambda txt: received_insert.append(txt))
        self.dialog.signal_save_as_card.connect(lambda title, content: received_card.append((title, content)))

        self.dialog.last_assistant_reply = "測試回覆內容"
        self.dialog._insert_to_editor()
        self.dialog._save_as_card()

        self.assertEqual(received_insert, ["測試回覆內容"])
        self.assertEqual(len(received_card), 1)
        self.assertEqual(received_card[0][1], "測試回覆內容")


if __name__ == "__main__":
    unittest.main()
