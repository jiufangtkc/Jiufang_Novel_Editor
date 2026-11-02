import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PyQt6.QtWidgets import QApplication

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from services.ai_worker import AIProofreadWorker, BaseAIWorker
from services.database import DatabaseService


class TestAIProofreadWorker(unittest.TestCase):
    """驗證純本機 AI 語意校稿背景執行緒 AIProofreadWorker"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_proofread.db")
        DatabaseService.init_db(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_worker_initialization(self):
        """測試 Worker 正確初始化與預設屬性"""
        text = "這是一段測試文本。"
        worker = AIProofreadWorker(
            text_content=text,
            chapter_name="第一章",
            node_id="node_123",
            options={"typo": True, "usage": False, "suggestion": True},
            chunk_size=1000
        )
        self.assertEqual(worker.text_content, text)
        self.assertEqual(worker.chapter_name, "第一章")
        self.assertEqual(worker.node_id, "node_123")
        self.assertEqual(worker.chunk_size, 1000)
        self.assertTrue(worker.options["typo"])
        self.assertFalse(worker.options["usage"])
        self.assertTrue(worker.options["suggestion"])
        self.assertFalse(worker._is_cancelled)

    def test_prompt_generation_options(self):
        """測試依據 options 勾選狀態動態組裝提示詞"""
        worker = AIProofreadWorker(
            text_content="測試",
            options={"typo": True, "usage": False, "suggestion": False}
        )
        prompt = worker._build_system_prompt()
        self.assertIn("「typo」", prompt)
        self.assertNotIn("「usage」", prompt)
        self.assertNotIn("「suggestion」", prompt)

        worker_all = AIProofreadWorker(
            text_content="測試",
            options={"typo": True, "usage": True, "suggestion": True}
        )
        prompt_all = worker_all._build_system_prompt()
        self.assertIn("「typo」", prompt_all)
        self.assertIn("「usage」", prompt_all)
        self.assertIn("「suggestion」", prompt_all)

    def test_split_into_chunks_short_text(self):
        """測試小於 chunk_size 的短文字不切分"""
        text = "春眠不覺曉，處處聞啼鳥。"
        chunks = AIProofreadWorker._split_into_chunks(text, max_chunk_size=100)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], (0, text))

    def test_split_into_chunks_multiline_long_text(self):
        """測試多行長文字按行切分並記錄正確的字元偏移量"""
        lines = [f"第 {i} 行長篇段落內容。\n" for i in range(10)]
        full_text = "".join(lines)
        # 單行長度約 12 字，設定 max_chunk_size=30，應切分為數個區段
        chunks = AIProofreadWorker._split_into_chunks(full_text, max_chunk_size=30)
        self.assertGreater(len(chunks), 1)

        # 驗證每個 chunk 重組後與原文完全一致
        reconstructed = "".join(chunk_text for _, chunk_text in chunks)
        self.assertEqual(reconstructed, full_text)

        # 驗證 offset 正確對齊
        for start_offset, chunk_text in chunks:
            self.assertEqual(full_text[start_offset:start_offset + len(chunk_text)], chunk_text)

    def test_split_into_chunks_oversized_single_line(self):
        """測試單行超長文字強制切分"""
        long_line = "甲" * 50
        chunks = AIProofreadWorker._split_into_chunks(long_line, max_chunk_size=20)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0], (0, "甲" * 20))
        self.assertEqual(chunks[1], (20, "甲" * 20))
        self.assertEqual(chunks[2], (40, "甲" * 10))

    def test_parse_proofread_json_valid_and_markdown(self):
        """測試 JSON 解析容錯：純 JSON 與 Markdown 包覆"""
        raw_json = '[{"category": "typo", "original_text": "在次", "suggestion": "再次", "reason": "錯字"}]'
        parsed = AIProofreadWorker._parse_proofread_json(raw_json)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["original_text"], "在次")

        # Markdown 包覆
        md_json = f"```json\n{raw_json}\n```"
        parsed_md = AIProofreadWorker._parse_proofread_json(md_json)
        self.assertEqual(len(parsed_md), 1)
        self.assertEqual(parsed_md[0]["suggestion"], "再次")

        # 前後多餘文字
        chatty_json = f"以下是為您找到的問題：\n{raw_json}\n希望對您有幫助！"
        parsed_chatty = AIProofreadWorker._parse_proofread_json(chatty_json)
        self.assertEqual(len(parsed_chatty), 1)
        self.assertEqual(parsed_chatty[0]["category"], "typo")

    def test_parse_proofread_json_invalid(self):
        """測試非合法 JSON 與空字串之安全防禦"""
        self.assertEqual(AIProofreadWorker._parse_proofread_json(""), [])
        self.assertEqual(AIProofreadWorker._parse_proofread_json("非 JSON 文字內容"), [])
        self.assertEqual(AIProofreadWorker._parse_proofread_json('{"key": "not a list"}'), [])

    def test_worker_run_success_and_offset_alignment(self):
        """測試推論流程成功、信號發射與字元位置校正"""
        text = "他走在街上，在次看見了那道光芒。"
        worker = AIProofreadWorker(
            text_content=text,
            chapter_name="第一章",
            node_id="node_1",
            chunk_size=1000
        )

        fake_model_output = json.dumps([
            {
                "category": "typo",
                "original_text": "在次",
                "suggestion": "再次",
                "reason": "副詞應為再次",
                "char_offset": 0,  # 故意給予不正確的 offset，驗證 Worker 能自動搜尋真實位置
                "match_len": 2
            }
        ])

        with patch("services.ai_worker.AIService.load_settings") as mock_settings, \
             patch("services.ai_worker.AIService.call_api_stream") as mock_stream:

            mock_settings.return_value = {
                "provider": "LM Studio",
                "api_urls": {"LM Studio": "http://localhost:1234/v1/chat/completions"},
                "api_keys": {"LM Studio": ""},
                "models": {"LM Studio": "local-model"}
            }

            def fake_stream(*args, **kwargs):
                yield fake_model_output

            mock_stream.side_effect = fake_stream

            finished_results = []
            progress_events = []
            worker.finished_signal.connect(lambda res: finished_results.extend(res))
            worker.progress_signal.connect(lambda cur, tot, msg: progress_events.append((cur, tot, msg)))

            worker.run()

            self.assertEqual(len(finished_results), 1)
            item = finished_results[0]
            self.assertEqual(item["category"], "typo")
            self.assertEqual(item["original_text"], "在次")
            self.assertEqual(item["suggestion"], "再次")
            # 「在次」在 "他走在街上，在次看見了那道光芒。" 中的索引應為 6
            self.assertEqual(item["char_offset"], 6)
            self.assertEqual(item["match_len"], 2)
            self.assertEqual(item["status"], "pending")
            self.assertEqual(len(progress_events), 1)

    def test_worker_cancellation(self):
        """測試 Worker 執行中途 cancel() 中斷機制"""
        text = "第一段文字。\n第二段文字。\n第三段文字。"
        worker = AIProofreadWorker(
            text_content=text,
            chunk_size=10
        )

        with patch("services.ai_worker.AIService.load_settings") as mock_settings, \
             patch("services.ai_worker.AIService.call_api_stream") as mock_stream:

            mock_settings.return_value = {
                "provider": "Ollama",
                "api_urls": {"Ollama": "http://localhost:11434/api/chat"},
                "api_keys": {"Ollama": ""},
                "models": {"Ollama": "qwen2.5"}
            }

            def fake_stream(*args, **kwargs):
                worker.cancel()
                yield '[]'

            mock_stream.side_effect = fake_stream

            finished_results = []
            worker.finished_signal.connect(lambda res: finished_results.extend(res))

            worker.run()

            self.assertTrue(worker._is_cancelled)
            self.assertEqual(len(finished_results), 0)

    def test_worker_error_signal(self):
        """測試未設定 API 網址時拋出異常並發送 error_signal"""
        worker = AIProofreadWorker(text_content="測試文本")

        with patch("services.ai_worker.AIService.load_settings") as mock_settings:
            mock_settings.return_value = {
                "provider": "Ollama",
                "api_urls": {"Ollama": ""},
                "api_keys": {"Ollama": ""},
                "models": {"Ollama": "qwen2.5"}
            }

            errors = []
            worker.error_signal.connect(lambda err: errors.append(err))

            worker.run()

            self.assertEqual(len(errors), 1)
            self.assertIn("尚未設定", errors[0])

    def test_controller_ignored_rules_filtering(self):
        """測試 Controller 接收校稿結果時，依據 proofread_ignored_rules 排除已忽略項目"""
        from controllers.ai_controller import AIController

        mock_mc = MagicMock()
        mock_mc.project.get_active_db_path.return_value = self.db_path
        mock_mc.stats.record_ai_activity = MagicMock()

        controller = AIController(mock_mc)
        controller.proofread_dialog = MagicMock()

        # 加入一筆已忽略規則：「typo」類別的「在次」
        DatabaseService.add_ignored_rule(self.db_path, "typo", "在次")

        # 模擬 Worker 回傳 2 筆結果
        mock_results = [
            {
                "id": "res_1",
                "category": "typo",
                "node_id": "node_1",
                "chapter_name": "第一章",
                "char_offset": 5,
                "match_len": 2,
                "original_text": "在次",
                "suggestion": "再次",
                "reason": "副詞應為再次",
                "status": "pending",
                "created_at": "2026-11-01T20:00:00"
            },
            {
                "id": "res_2",
                "category": "usage",
                "node_id": "node_1",
                "chapter_name": "第一章",
                "char_offset": 10,
                "match_len": 4,
                "original_text": "差強人意",
                "suggestion": "令人滿意",
                "reason": "原意為尚能令人滿意，常被誤用",
                "status": "pending",
                "created_at": "2026-11-01T20:00:00"
            }
        ]

        controller._on_proofread_finished(mock_results)

        # 驗證資料庫中的結果：「在次」已被過濾，僅存入「差強人意」
        saved_items = DatabaseService.load_proofread_results(self.db_path)
        self.assertEqual(len(saved_items), 1)
        self.assertEqual(saved_items[0]["original_text"], "差強人意")
        controller.proofread_dialog.finish_proofreading.assert_called_once()
        mock_mc.stats.record_ai_activity.assert_called_once_with(chat_count=1, feature_key="proofread")

    def test_controller_handle_start_proofread_starts_worker(self):
        """測試 Controller.handle_start_proofread 正確初始化 Worker 並非同步啟動"""
        from controllers.ai_controller import AIController

        mock_mc = MagicMock()
        mock_mc.project.get_active_db_path.return_value = self.db_path
        mock_mc.tree.get_item_id.return_value = "node_chapter_1"
        mock_file_item = MagicMock()
        mock_file_item.text.return_value = "第一章"
        mock_mc.current_file_item = mock_file_item

        controller = AIController(mock_mc)
        controller.proofread_dialog = MagicMock()
        controller.view = MagicMock()
        controller.view.editor.toPlainText.return_value = "章節正文內容..."

        with patch.object(AIProofreadWorker, "start") as mock_start:
            controller.handle_start_proofread("目前章節", {"typo": True, "usage": True, "suggestion": True})
            self.assertIsNotNone(controller.proofread_worker)
            self.assertEqual(controller.proofread_worker.text_content, "章節正文內容...")
            self.assertEqual(controller.proofread_worker.node_id, "node_chapter_1")
            self.assertEqual(controller.proofread_worker.chapter_name, "第一章")
            mock_start.assert_called_once()

    def test_controller_handle_start_proofread_empty_text(self):
        """測試 Controller.handle_start_proofread 遇到空文字時不啟動 Worker 並重設按鈕"""
        from controllers.ai_controller import AIController

        mock_mc = MagicMock()
        mock_mc.project.get_active_db_path.return_value = self.db_path
        mock_mc.current_file_item = None

        controller = AIController(mock_mc)
        controller.proofread_dialog = MagicMock()
        controller.view = MagicMock()
        controller.view.editor.toPlainText.return_value = "   "

        with patch("PyQt6.QtWidgets.QMessageBox.information") as mock_info:
            controller.handle_start_proofread("目前章節", {"typo": True})
            self.assertIsNone(controller.proofread_worker)
            mock_info.assert_called_once()
            controller.proofread_dialog.finish_proofreading.assert_called_once()


if __name__ == "__main__":
    unittest.main()
