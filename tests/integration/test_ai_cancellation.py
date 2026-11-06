import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.ai_worker import BaseAIWorker, AIProofreadWorker


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


def test_ai_proofread_worker_stream_cancellation():
    """測試 AIProofreadWorker 在串流生成中被取消時不會發射 finished_signal"""
    worker = AIProofreadWorker(
        text_content="這是一段測試文字。",
        chapter_name="第一章",
        node_id="node_1"
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
            yield '[{"category": "typo",'
            worker.cancel()
            yield '"original_text": "測試"}]'

        mock_stream.side_effect = fake_stream

        finished_signals = []
        worker.finished_signal.connect(lambda res: finished_signals.append(res))

        worker.run()

        assert worker._is_cancelled is True
        assert len(finished_signals) == 0
