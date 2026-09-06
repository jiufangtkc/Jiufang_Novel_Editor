import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from services.ai_settings_service import AISettingsService, DEFAULT_SETTINGS, SETTINGS_FILENAME
from services.ai_worker import AIWorker, AIChatWorker, AIContinuationWorker, AIStreamWorker
from services.ai_service import AIService


class TestAISettingsAndWorker(unittest.TestCase):
    """驗證 SLIM-3 拆分之 AISettingsService 與 AIWorker 各背景執行緒模組。"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings_file = os.path.join(self.temp_dir.name, SETTINGS_FILENAME)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_settings_service_load_and_save(self):
        """測試 AISettingsService 設定檔儲存與讀取正確性。"""
        settings = dict(DEFAULT_SETTINGS)
        settings["provider"] = "Anthropic"
        settings["timeout"] = 120
        settings["api_keys"]["Anthropic"] = "test-anthropic-key"

        AISettingsService.save_settings(settings, file_path=self.settings_file)
        self.assertTrue(os.path.exists(self.settings_file))

        loaded = AISettingsService.load_settings(file_path=self.settings_file)
        self.assertEqual(loaded["provider"], "Anthropic")
        self.assertEqual(loaded["timeout"], 120)
        self.assertEqual(loaded["api_keys"]["Anthropic"], "test-anthropic-key")

    def test_aiservice_delegates_to_settings_service(self):
        """測試 AIService 對外介面與 AISettingsService 委派保持一致。"""
        settings = dict(DEFAULT_SETTINGS)
        settings["provider"] = "Ollama"
        settings["models"]["Ollama"] = "qwen2.5:14b"

        AIService.save_settings(settings, file_path=self.settings_file)
        loaded = AIService.load_settings(file_path=self.settings_file)
        self.assertEqual(loaded["provider"], "Ollama")
        self.assertEqual(loaded["models"]["Ollama"], "qwen2.5:14b")

    def test_worker_initialization(self):
        """測試各背景執行緒類別之初始化與取消狀態管理。"""
        # AIWorker
        worker = AIWorker(task_type="impression", text_content="小說正文內容", chapter_title="第一章")
        self.assertEqual(worker.task_type, "impression")
        self.assertEqual(worker.chapter_title, "第一章")
        self.assertFalse(worker._is_cancelled)
        worker.cancel()
        self.assertTrue(worker._is_cancelled)

        # AIChatWorker
        chat_worker = AIChatWorker(messages=[{"role": "user", "content": "你好"}])
        self.assertEqual(len(chat_worker.messages), 1)
        self.assertFalse(chat_worker._is_cancelled)
        chat_worker.cancel()
        self.assertTrue(chat_worker._is_cancelled)

        # AIContinuationWorker
        continuation_worker = AIContinuationWorker(context_text="續寫上文")
        self.assertEqual(continuation_worker.context_text, "續寫上文")

        # AIStreamWorker
        stream_worker = AIStreamWorker(system_prompt="系統提示詞", user_content="使用者問題")
        self.assertFalse(stream_worker._is_cancelled)
        stream_worker.cancel()
        self.assertTrue(stream_worker._is_cancelled)


if __name__ == "__main__":
    unittest.main()
