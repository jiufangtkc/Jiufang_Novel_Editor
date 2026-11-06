import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PyQt6.QtWidgets import QApplication

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from services.ai_settings_service import AISettingsService, DEFAULT_SETTINGS, SETTINGS_FILENAME
from services.ai_worker import BaseAIWorker, AIProofreadWorker
from services.ai_service import AIService


class TestAISettingsAndWorker(unittest.TestCase):
    """驗證 AISettingsService 與本機 AIProofreadWorker 模組整合。"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings_file = os.path.join(self.temp_dir.name, SETTINGS_FILENAME)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_settings_service_load_and_save(self):
        """測試 AISettingsService 設定檔儲存與讀取正確性。"""
        settings = dict(DEFAULT_SETTINGS)
        settings["provider"] = "LM Studio"
        settings["timeout"] = 120
        settings["models"]["LM Studio"] = "qwen2.5-7b"

        AISettingsService.save_settings(settings, file_path=self.settings_file)
        self.assertTrue(os.path.exists(self.settings_file))

        loaded = AISettingsService.load_settings(file_path=self.settings_file)
        self.assertEqual(loaded["provider"], "LM Studio")
        self.assertEqual(loaded["timeout"], 120)
        self.assertEqual(loaded["models"]["LM Studio"], "qwen2.5-7b")

    def test_aiservice_delegates_to_settings_service(self):
        """測試 AIService 對外介面與 AISettingsService 委派保持一致。"""
        settings = dict(DEFAULT_SETTINGS)
        settings["provider"] = "Ollama"
        settings["models"]["Ollama"] = "qwen2.5:14b"

        AIService.save_settings(settings, file_path=self.settings_file)
        loaded = AIService.load_settings(file_path=self.settings_file)
        self.assertEqual(loaded["provider"], "Ollama")
        self.assertEqual(loaded["models"]["Ollama"], "qwen2.5:14b")

    def test_worker_initialization_and_cancel(self):
        """測試 BaseAIWorker 與 AIProofreadWorker 之初始化與取消狀態管理。"""
        base_worker = BaseAIWorker()
        self.assertFalse(base_worker._is_cancelled)
        base_worker.cancel()
        self.assertTrue(base_worker._is_cancelled)

        proofread_worker = AIProofreadWorker(text_content="小說正文內容", chapter_name="第一章", node_id="n1")
        self.assertEqual(proofread_worker.chapter_name, "第一章")
        self.assertFalse(proofread_worker._is_cancelled)
        proofread_worker.cancel()
        self.assertTrue(proofread_worker._is_cancelled)

    def test_ai_settings_dialog_context_limit(self):
        """測試 AISettingsDialog 能夠正確讀取並儲存 Context 上限設定"""
        from views.dialogs.ai_settings_dialog import AISettingsDialog

        fake_settings = dict(DEFAULT_SETTINGS)
        fake_settings["provider"] = "LM Studio"
        fake_settings["context_limits"]["LM Studio"] = 131072

        with patch("services.ai_service.AIService.load_settings", return_value=fake_settings):
            dlg = AISettingsDialog()
            self.assertEqual(dlg.spin_context_limit.value(), 131072)

            dlg.spin_context_limit.setValue(65536)
            dlg._save_current_provider_fields("LM Studio")
            self.assertEqual(dlg.settings["context_limits"]["LM Studio"], 65536)
            dlg.close()


if __name__ == "__main__":
    unittest.main()
