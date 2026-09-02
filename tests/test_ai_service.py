import os
import sys
import json
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ai_service import AIService, DEFAULT_SETTINGS


class TestAIService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings_file = os.path.join(self.temp_dir.name, "ai_settings_test.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_settings_contains_openai_and_features(self):
        settings = dict(DEFAULT_SETTINGS)
        self.assertIn("OpenAI", settings["api_urls"])
        self.assertIn("OpenAI", settings["models"])
        self.assertEqual(settings["api_urls"]["OpenAI"], "https://api.openai.com/v1/chat/completions")
        self.assertEqual(settings["models"]["OpenAI"], "gpt-4o")
        self.assertIn("chat", settings["prompts"])
        self.assertIn("continuation", settings["prompts"])
        self.assertFalse(settings["ai_continuation_enabled"])
        self.assertFalse(settings["ai_continuation_agreed"])

    def test_load_and_save_settings(self):
        custom_settings = dict(DEFAULT_SETTINGS)
        custom_settings["provider"] = "OpenAI"
        custom_settings["api_keys"]["OpenAI"] = "sk-test-mock-key-12345"
        custom_settings["timeout"] = 600
        custom_settings["ai_continuation_enabled"] = True

        AIService.save_settings(custom_settings, file_path=self.settings_file)
        self.assertTrue(os.path.exists(self.settings_file))

        loaded = AIService.load_settings(file_path=self.settings_file)
        self.assertEqual(loaded["provider"], "OpenAI")
        self.assertEqual(loaded["api_keys"]["OpenAI"], "sk-test-mock-key-12345")
        self.assertEqual(loaded["timeout"], 600)
        self.assertEqual(loaded["models"]["OpenAI"], "gpt-4o")
        self.assertTrue(loaded["ai_continuation_enabled"])

    def test_detect_local_models_empty_or_offline(self):
        # 測試空 URL
        self.assertEqual(AIService.detect_local_models("Ollama", ""), [])

        # 測試離線或連線異常時安全回傳空串列而不崩潰
        from unittest.mock import patch
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
            models = AIService.detect_local_models("Ollama", "http://127.0.0.1:99999/api/chat", timeout=1)
            self.assertIsInstance(models, list)
            self.assertEqual(len(models), 0)

            models_lm = AIService.detect_local_models("LM Studio", "http://127.0.0.1:99999/v1/chat/completions", timeout=1)
            self.assertIsInstance(models_lm, list)
            self.assertEqual(len(models_lm), 0)


if __name__ == "__main__":
    unittest.main()
