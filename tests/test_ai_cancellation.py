import os
import sys
import time
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.ai_pipeline_workers import LongTextPipelineWorker
from services.ai_worker import AIWorker, AIChatWorker, AIStreamWorker, BaseAIWorker


def test_base_ai_worker_cancel_closes_active_response():
    """測試 BaseAIWorker 在 cancel() 時會主動關閉 response 與底層 raw socket"""
    worker = BaseAIWorker()
    mock_resp = MagicMock()
    mock_raw = MagicMock()
    mock_resp.raw = mock_raw

    worker._set_active_response(mock_resp)
    assert worker._active_response is mock_resp

    worker.cancel()
    assert worker._is_cancelled is True
    mock_raw.close.assert_called_once()
    mock_resp.close.assert_called_once()
    assert worker._active_response is None


def test_long_text_pipeline_worker_cancellation():
    """測試 LongTextPipelineWorker 在執行途中取消時不會發射 finished_signal，並主動中斷連線"""
    text = "這是一段長篇小說測試文字。" * 150
    worker = LongTextPipelineWorker(
        task_type="character",
        text_content=text,
        chapter_title="測試章節",
        threshold=2
    )

    mock_resp = MagicMock()
    mock_raw = MagicMock()
    mock_resp.raw = mock_raw

    with patch("services.ai_pipeline_workers.AIService.load_settings") as mock_settings, \
         patch("services.ai_pipeline_workers.AIService.call_api") as mock_call_api:

        mock_settings.return_value = {
            "provider": "LM Studio",
            "api_urls": {"LM Studio": "http://localhost:1234/v1/chat/completions"},
            "api_keys": {"LM Studio": ""},
            "models": {"LM Studio": "qwen2.5"}
        }

        def mock_call(provider, api_url, api_key, model, system_prompt, user_content, timeout,
                      is_cancelled_callback=None, on_response_ready=None):
            if on_response_ready:
                on_response_ready(mock_resp)
            # 模擬收到取消
            worker.cancel()
            assert is_cancelled_callback() is True
            return ""

        mock_call_api.side_effect = mock_call

        finished_signals = []
        worker.finished_signal.connect(lambda res: finished_signals.append(res))

        worker.run()

        # 驗證連線被主動 close
        mock_raw.close.assert_called_once()
        mock_resp.close.assert_called_once()
        # 驗證未發送 finished_signal
        assert len(finished_signals) == 0


def test_ai_worker_stream_cancellation():
    """測試 AIWorker 在短文串流生成中被取消時不會發射 finished_signal"""
    worker = AIWorker(
        task_type="impression",
        text_content="短篇測試",
        chunk_threshold=5000
    )

    with patch("services.ai_worker.AIService.load_settings") as mock_settings, \
         patch("services.ai_worker.AIService.call_api_stream") as mock_stream:

        mock_settings.return_value = {
            "provider": "LM Studio",
            "api_urls": {"LM Studio": "http://localhost:1234/v1/chat/completions"},
            "api_keys": {"LM Studio": ""},
            "models": {"LM Studio": "test-model"}
        }

        def fake_stream(*args, **kwargs):
            yield "片段一"
            # 產生第一個片段後由外界觸發 cancel
            worker.cancel()
            yield "片段二"

        mock_stream.side_effect = fake_stream

        finished_signals = []
        worker.finished_signal.connect(lambda res: finished_signals.append(res))

        worker.run()

        assert worker._is_cancelled is True
        assert len(finished_signals) == 0


def test_ai_chat_worker_cancellation():
    """測試 AIChatWorker 在多輪對話中被取消時正確停止且不發射 finished_signal"""
    worker = AIChatWorker(messages=[{"role": "user", "content": "你好"}])

    with patch("services.ai_worker.AIService.load_settings") as mock_settings, \
         patch("services.ai_worker.AIService.call_api_stream") as mock_stream:

        mock_settings.return_value = {
            "provider": "LM Studio",
            "api_urls": {"LM Studio": "http://localhost:1234/v1/chat/completions"},
            "api_keys": {"LM Studio": ""},
            "models": {"LM Studio": "test-model"}
        }

        def fake_stream(*args, **kwargs):
            yield "你"
            worker.cancel()
            yield "好"

        mock_stream.side_effect = fake_stream

        finished_signals = []
        worker.finished_signal.connect(lambda res: finished_signals.append(res))

        worker.run()

        assert worker._is_cancelled is True
        assert len(finished_signals) == 0


def test_ai_stream_worker_cancellation():
    """測試 AIStreamWorker 在擴寫流式生成中被取消時不發射 finished_signal"""
    worker = AIStreamWorker(system_prompt="續寫", user_content="上文")

    with patch("services.ai_worker.AIService.load_settings") as mock_settings, \
         patch("services.ai_worker.AIService.call_api_stream") as mock_stream:

        mock_settings.return_value = {
            "provider": "LM Studio",
            "api_urls": {"LM Studio": "http://localhost:1234/v1/chat/completions"},
            "api_keys": {"LM Studio": ""},
            "models": {"LM Studio": "test-model"}
        }

        def fake_stream(*args, **kwargs):
            yield "續寫字詞"
            worker.cancel()
            yield "多餘字詞"

        mock_stream.side_effect = fake_stream

        finished_signals = []
        worker.finished_signal.connect(lambda res: finished_signals.append(res))

        worker.run()

        assert worker._is_cancelled is True
        assert len(finished_signals) == 0
