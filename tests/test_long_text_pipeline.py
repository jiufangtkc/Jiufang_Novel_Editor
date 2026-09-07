import json
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from unittest.mock import patch, MagicMock
from services.ai_pipeline_workers import LongTextPipelineWorker

def test_long_text_pipeline_worker_character():
    # 建立超過分段大小的測試長文
    text = "這是一段很長很長的故事。" * 200
    
    worker = LongTextPipelineWorker(
        task_type="character",
        text_content=text,
        chapter_title="測試章節",
        threshold=2
    )
    
    # Mock AIService call_api 和 settings
    with patch("services.ai_pipeline_workers.AIService.load_settings") as mock_settings, \
         patch("services.ai_pipeline_workers.AIService.call_api") as mock_call_api:
         
        mock_settings.return_value = {
            "provider": "MockProvider",
            "api_urls": {"MockProvider": "http://localhost"},
            "api_keys": {"MockProvider": "test_key"}
        }
        
        # 階段1回傳候選字串, 階段2回傳 JSON diff
        def side_effect(provider, api_url, api_key, model, system_prompt, user_content, timeout, *args, **kwargs):
            if "實體名詞" in system_prompt:
                return "小明, 小華, 小明"
            else:
                return json.dumps({"小明": {"外貌": "很高", "性格": "開朗"}})
                
        mock_call_api.side_effect = side_effect
        
        signals = []
        worker.progress_signal.connect(lambda c, t, m: signals.append(m))
        worker.finished_signal.connect(lambda res: signals.append(res))
        
        worker.run()
        
        assert any("階段 0/4" in m for m in signals if isinstance(m, str))
        assert any("階段 3/4" in m for m in signals if isinstance(m, str))
        
        # 確認送出了最終結果
        final_res = [m for m in signals if isinstance(m, dict)]
        assert len(final_res) == 1
        assert final_res[0]["task_type"] == "character"
        # 因為是 character 任務，內部 parse 會把狀態庫轉成 characters 陣列
        assert len(final_res[0]["characters"]) == 1
        assert final_res[0]["characters"][0]["name"] == "小明"

def test_long_text_pipeline_worker_impression():
    text = "這是一段很長很長的故事。" * 200
    
    worker = LongTextPipelineWorker(
        task_type="impression",
        text_content=text,
        threshold=2
    )
    
    with patch("services.ai_pipeline_workers.AIService.load_settings") as mock_settings, \
         patch("services.ai_pipeline_workers.AIService.call_api") as mock_call_api:
         
        mock_settings.return_value = {
            "provider": "MockProvider",
            "api_urls": {"MockProvider": "http://localhost"},
            "api_keys": {"MockProvider": "test_key"}
        }
        
        # 模擬不同回傳
        def side_effect(provider, api_url, api_key, model, system_prompt, user_content, timeout, *args, **kwargs):
            if "實體名詞" in system_prompt:
                return "主題A, 主題A"
            else:
                return json.dumps({"評語": "寫得很好"})
                
        mock_call_api.side_effect = side_effect
        
        signals = []
        worker.finished_signal.connect(lambda res: signals.append(res))
        worker.run()
        
        final_res = [m for m in signals if isinstance(m, dict)]
        assert len(final_res) == 1
        assert final_res[0]["task_type"] == "impression"
        assert final_res[0]["category"] == "summary"
        assert "評語" in final_res[0]["content"]
