import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PyQt6.QtWidgets import QApplication

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from services.ai_service import AIService, DEFAULT_SETTINGS


class TestAIService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings_file = os.path.join(self.temp_dir.name, "ai_settings_test.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_settings_contains_local_providers(self):
        settings = dict(DEFAULT_SETTINGS)
        self.assertEqual(settings["provider"], "Ollama")
        self.assertIn("Ollama", settings["api_urls"])
        self.assertIn("LM Studio", settings["api_urls"])
        self.assertEqual(settings["api_urls"]["Ollama"], "http://localhost:11434/api/chat")
        self.assertEqual(settings["api_urls"]["LM Studio"], "http://localhost:1234/v1/chat/completions")
        self.assertIn("Ollama", settings["models"])
        self.assertIn("LM Studio", settings["models"])

    def test_load_and_save_settings(self):
        custom_settings = dict(DEFAULT_SETTINGS)
        custom_settings["provider"] = "LM Studio"
        custom_settings["timeout"] = 600
        custom_settings["models"]["LM Studio"] = "qwen2.5-7b-instruct"

        AIService.save_settings(custom_settings, file_path=self.settings_file)
        self.assertTrue(os.path.exists(self.settings_file))

        loaded = AIService.load_settings(file_path=self.settings_file)
        self.assertEqual(loaded["provider"], "LM Studio")
        self.assertEqual(loaded["timeout"], 600)
        self.assertEqual(loaded["models"]["LM Studio"], "qwen2.5-7b-instruct")

    def test_detect_local_models_empty_or_offline(self):
        self.assertEqual(AIService.detect_local_models("Ollama", ""), [])

        import requests
        with patch("services.ai_service.requests.get", side_effect=requests.exceptions.ConnectionError("Connection refused")):
            models = AIService.detect_local_models("Ollama", "http://127.0.0.1:99999/api/chat", timeout=1)
            self.assertIsInstance(models, list)
            self.assertEqual(len(models), 0)

            models_lm = AIService.detect_local_models("LM Studio", "http://127.0.0.1:99999/v1/chat/completions", timeout=1)
            self.assertIsInstance(models_lm, list)
            self.assertEqual(len(models_lm), 0)

    def test_get_settings_file_path_appdata(self):
        path = AIService.get_settings_file_path()
        self.assertTrue(path.endswith("ai_settings.json"))
        self.assertIn("Jiufang_Novel_Editor", path)

        custom_path = AIService.get_settings_file_path(self.temp_dir.name)
        self.assertEqual(custom_path, os.path.join(self.temp_dir.name, "ai_settings.json"))

    def test_count_tokens_ollama_fallback_on_missing_endpoint(self):
        """驗證 Ollama tokenize 端點不存在（連線異常）時靜默 fallback 到本機保守估算值"""
        import requests as req_module

        text = "這是一段測試文字，用來驗證 Token 計算的 Fallback 機制。"
        expected_fallback = AIService.fast_estimate_tokens(text)

        with patch("services.ai_service.requests.post", side_effect=req_module.exceptions.ConnectionError("Connection refused")):
            result = AIService.count_tokens("Ollama", "http://127.0.0.1:11434/api/generate", text, timeout=1)
            self.assertEqual(result, expected_fallback)

    def test_count_tokens_ollama_success(self):
        """驗證 Ollama tokenize 端點成功回應時正確回傳 tokens 列表長度"""
        text = "主角在古老遺跡中發現了封印已久的神器。"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"tokens": list(range(18))}

        with patch("services.ai_service.requests.post", return_value=mock_response):
            result = AIService.count_tokens("Ollama", "http://127.0.0.1:11434/api/generate", text, timeout=5)
            self.assertEqual(result, 18)

    def test_count_tokens_lm_studio_no_network(self):
        """驗證 LM Studio 直接使用本機零延遲估算，絕不對外發送 /v1/tokenize 請求"""
        text = "這是一段測試小說內文，莫庸持劍走向星空深處。"
        with patch("services.ai_service.requests.post") as mock_post:
            result = AIService.count_tokens("LM Studio", "http://localhost:1234/v1/chat/completions", text)
            mock_post.assert_not_called()
            self.assertEqual(result, AIService.fast_estimate_tokens(text))
            self.assertGreater(result, 0)

    def test_fetch_context_limit_lm_studio(self):
        """測試向 LM Studio /api/v0/models 正確解析 loaded_context_length"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "qwen3.5-9b-uncensored",
                    "state": "loaded",
                    "max_context_length": 262144,
                    "loaded_context_length": 131072
                }
            ]
        }

        with patch("services.ai_service.requests.get", return_value=mock_resp):
            limit = AIService.fetch_context_limit("LM Studio", "http://localhost:1234/v1/chat/completions")
            self.assertEqual(limit, 131072)

    def test_fetch_context_limit_offline(self):
        """測試當本機端點離線或錯誤時，安全回傳 None"""
        with patch("services.ai_service.requests.get", side_effect=Exception("Connection refused")):
            limit = AIService.fetch_context_limit("LM Studio", "http://localhost:1234/v1/chat/completions", timeout=0.1)
            self.assertIsNone(limit)

    def test_check_local_server_status_online(self):
        """測試當本機端點正常回應時，check_local_server_status 回傳 (True, '連線正常')"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("services.ai_service.requests.get", return_value=mock_resp):
            online, msg = AIService.check_local_server_status("LM Studio", "http://localhost:1234/v1/chat/completions")
            self.assertTrue(online)
            self.assertEqual(msg, "連線正常")

    def test_check_local_server_status_offline(self):
        """測試當本機端點連線遭拒時，check_local_server_status 正確回傳 (False, 錯誤訊息)"""
        import requests

        with patch("services.ai_service.requests.get", side_effect=requests.exceptions.ConnectionError("Connection refused")):
            online, msg = AIService.check_local_server_status("LM Studio", "http://localhost:1234/v1/chat/completions")
            self.assertFalse(online)
            self.assertIn("未啟動", msg)


if __name__ == "__main__":
    unittest.main()
