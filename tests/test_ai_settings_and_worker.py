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

    def test_workers_run_without_name_error(self):
        """測試各背景執行緒在執行 run() 時，能正確透過 AIService 呼叫 API 且不發生 NameError。"""
        from unittest.mock import patch

        dummy_settings = {
            "provider": "LM Studio",
            "timeout": 30,
            "api_urls": {"LM Studio": "http://localhost:1234/v1/chat/completions"},
            "api_keys": {"LM Studio": ""},
            "models": {"LM Studio": "test-model"},
            "prompts": {"chat": "你是一位小說助手"}
        }

        with patch.object(AIService, 'load_settings', return_value=dummy_settings):
            # 1. 測試 AIChatWorker.run()
            with patch.object(AIService, 'call_api_stream', return_value=iter(["這是", "測試", "回覆"])):
                chat_worker = AIChatWorker(messages=[{"role": "user", "content": "樞機是什麼意思？"}])
                chunks = []
                finished_text = []
                chat_worker.chunk_signal.connect(chunks.append)
                chat_worker.finished_signal.connect(finished_text.append)
                chat_worker.run()
                self.assertEqual("".join(chunks), "這是測試回覆")
                self.assertEqual(finished_text, ["這是測試回覆"])

            # 2. 測試 AIContinuationWorker.run()
            with patch.object(AIService, 'call_api', return_value="接續的內容"):
                cont_worker = AIContinuationWorker(context_text="前情提要")
                cont_results = []
                cont_worker.finished_signal.connect(cont_results.append)
                cont_worker.run()
                self.assertEqual(cont_results, ["接續的內容"])

            # 3. 測試 AIStreamWorker.run()
            with patch.object(AIService, 'call_api_stream', return_value=iter(["流式", "產出"])):
                stream_worker = AIStreamWorker(system_prompt="sys", user_content="usr")
                stream_chunks = []
                stream_results = []
                stream_worker.chunk_received_signal.connect(stream_chunks.append)
                stream_worker.finished_signal.connect(stream_results.append)
                stream_worker.run()
                self.assertEqual("".join(stream_chunks), "流式產出")
                self.assertEqual(stream_results, ["流式產出"])

            # 4. 測試 AIWorker.run()
            with patch.object(AIService, 'call_api_stream', return_value=iter(["分析", "完成"])):
                analysis_worker = AIWorker(task_type="impression", text_content="短文分析內容")
                analysis_results = []
                analysis_worker.finished_signal.connect(analysis_results.append)
                analysis_worker.run()
                self.assertEqual(len(analysis_results), 1)
                self.assertEqual(analysis_results[0]["content"], "分析完成")

    def test_ai_worker_handles_memory_error(self):
        """測試 AIWorker 在遇到 MemoryError 時，能攔截並發射友善之 UI 降級提示訊號。"""
        from unittest.mock import patch
        from services.long_text_analyzer import LongTextAnalyzer

        dummy_settings = {
            "provider": "LM Studio",
            "api_urls": {"LM Studio": "http://localhost:1234/v1/chat/completions"},
            "api_keys": {"LM Studio": ""},
            "models": {"LM Studio": "test-model"},
            "prompts": {"impression": "請分析"}
        }

        with patch.object(AIService, 'load_settings', return_value=dummy_settings):
            with patch.object(LongTextAnalyzer, 'calculate_dynamic_chunk_size', side_effect=MemoryError("系統記憶體不足")):
                worker = AIWorker(task_type="impression", text_content="很長很長的文本" * 500, chunk_threshold=100)
                error_msgs = []
                worker.error_signal.connect(error_msgs.append)
                worker.run()

                self.assertEqual(len(error_msgs), 1)
                self.assertIn("記憶體不足", error_msgs[0])
                self.assertIn("系統記憶體不足", error_msgs[0])


if __name__ == "__main__":
    unittest.main()
